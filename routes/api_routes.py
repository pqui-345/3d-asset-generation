import os
import json
import uuid
import base64
import io

import werkzeug
from flask import Blueprint, request, jsonify, current_app, send_from_directory, send_file

from services.db_service import db_service
from services.bg_remover import BGRemoverService

# Singleton services
template_service = None
_template_service_loaded = False

def get_template_service():
    global template_service, _template_service_loaded
    if not _template_service_loaded:
        _template_service_loaded = True
        try:
            from services.template_service import TemplateService
            import torch
            template_service = TemplateService(
                template_dir=os.path.join(current_app.root_path, 'static', 'templates'),
                index_path=os.path.join(current_app.root_path, 'data', 'template_index.faiss'),
                metadata_db=os.path.join(current_app.root_path, 'data', 'template_metadata.sqlite'),
                device='cuda' if torch.cuda.is_available() else 'cpu'
            )
        except Exception as e:
            print(f"[WARNING] Template service unavailable: {e}")
    return template_service

def _get_local_triposr():
    try:
        from services.local_tripo_service import local_tripo_service
        return local_tripo_service
    except Exception as e:
        print(f"[PIPELINE] local_tripo_service not available: {e}")
        return None

api_bp = Blueprint('api', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@api_bp.route('/api/upload', methods=['POST'])
def upload_image():
    """Handles multi-image upload and initializes database entry."""
    files = request.files.getlist('files')
    if not files or len(files) == 0:
        return jsonify({"error": "No files provided"}), 400

    upload_dir = os.path.join(current_app.root_path, 'static', 'uploads')
    os.makedirs(upload_dir, exist_ok=True)

    asset_name = request.form.get('name', 'Unlabeled Object')
    if not asset_name or asset_name.strip() == '':
        asset_name = 'Unlabeled Object'

    asset_style = request.form.get('style', 'template_retrieval')

    saved_originals = []
    for f in files:
        if f and allowed_file(f.filename):
            ext = f.filename.rsplit('.', 1)[1].lower()
            filename_base = f"asset_{uuid.uuid4().hex}"
            filename_orig = f"{filename_base}_original.{ext}"
            original_path = os.path.join(upload_dir, filename_orig)
            f.save(original_path)
            saved_originals.append(f"/static/uploads/{filename_orig}")

    if not saved_originals:
        return jsonify({"error": "No valid files uploaded"}), 400

    primary_image = saved_originals[0]
    additional_images = saved_originals[1:] if len(saved_originals) > 1 else []

    sql = """
        INSERT INTO assets (name, original_image, additional_images, no_bg_image, model_glb, model_obj, model_ply, file_size, style)
        VALUES (%s, %s, %s, '', '', '', '', '0 MB', %s)
    """
    asset_id = db_service.execute(sql, (asset_name, primary_image, json.dumps(additional_images), asset_style))

    return jsonify({
        "success": True,
        "asset_id": asset_id,
        "name": asset_name,
        "original_image": primary_image,
        "additional_images": additional_images,
        "total_images": len(saved_originals)
    })


@api_bp.route('/api/bg-remove', methods=['POST'])
def remove_background():
    """Triggers background removal service for primary + additional images."""
    data = request.json or {}
    asset_id = data.get('asset_id')

    if not asset_id:
        return jsonify({"error": "Missing asset_id"}), 400

    asset = db_service.query("SELECT * FROM assets WHERE id = %s", (asset_id,), fetchone=True)
    if not asset:
        return jsonify({"error": "Asset not found"}), 404

    original_rel_path = asset['original_image']
    additional_raw = asset.get('additional_images', '[]')
    additional_images = json.loads(additional_raw) if isinstance(additional_raw, str) else additional_raw

    upload_dir = os.path.join(current_app.root_path, 'static', 'uploads')
    os.makedirs(upload_dir, exist_ok=True)

    def do_remove(rel_path):
        abs_path = os.path.join(current_app.root_path, rel_path.lstrip('/'))
        filename_base = os.path.basename(abs_path).rsplit('_original.', 1)[0]
        filename_nobg = f"{filename_base}_nobg.png"
        nobg_abs = os.path.join(upload_dir, filename_nobg)
        nobg_rel = f"/static/uploads/{filename_nobg}"
        success = BGRemoverService.remove_background(abs_path, nobg_abs)
        return nobg_rel if success else None

    primary_nobg = do_remove(original_rel_path)
    if not primary_nobg:
        return jsonify({"error": "Failed to remove background from primary image"}), 500

    additional_nobg = []
    for img_rel in additional_images:
        nobg = do_remove(img_rel)
        if nobg:
            additional_nobg.append(nobg)

    db_service.execute(
        "UPDATE assets SET no_bg_image = %s, additional_images = %s WHERE id = %s",
        (primary_nobg, json.dumps(additional_nobg), asset_id)
    )

    return jsonify({
        "success": True,
        "asset_id": asset_id,
        "no_bg_image": primary_nobg,
        "additional_nobg_count": len(additional_nobg)
    })


@api_bp.route('/api/generate-3d', methods=['POST'])
def generate_3d():
    data = request.json or {}
    asset_id = data.get('asset_id')
    if not asset_id:
        return jsonify({"error": "Missing asset_id"}), 400

    asset = db_service.query("SELECT * FROM assets WHERE id = %s", (asset_id,), fetchone=True)
    if not asset:
        return jsonify({"error": "Asset not found"}), 404

    no_bg_rel_path = asset['no_bg_image']
    if not no_bg_rel_path:
        return jsonify({"error": "Background has not been removed yet"}), 400

    no_bg_abs_path = os.path.join(current_app.root_path, no_bg_rel_path.lstrip('/'))
    models_dir = os.path.join(current_app.root_path, 'static', 'models')
    os.makedirs(models_dir, exist_ok=True)

    additional_raw = asset.get('additional_images', '[]')
    additional_nobg = json.loads(additional_raw) if isinstance(additional_raw, str) else additional_raw
    additional_abs = [os.path.join(current_app.root_path, p.lstrip('/')) for p in additional_nobg]

    asset_slug = f"model_{asset_id}_{uuid.uuid4().hex[:6]}"
    results = None
    method_used = "none"

    asset_style = asset.get('style', 'template_retrieval')
    print(f"[PIPELINE] Selected style/method: {asset_style}")

    # Reject deprecated procedural styles
    if asset_style in ('elliptical', 'extruded', 'procedural_elliptical', 'procedural_extruded'):
        return jsonify({
            "success": False,
            "error": "Phương pháp này không còn được hỗ trợ. Hãy chọn CLIP Template hoặc TripoSR GPU."
        }), 400

    if asset_style == 'local_triposr_gpu':
        lts = _get_local_triposr()
        if lts and lts.is_available():
            try:
                print("[PIPELINE] Running Local TripoSR GPU Offline...")
                # Collect ALL available no-bg image paths
                all_image_paths = [no_bg_abs_path] + additional_abs
                print(f"[PIPELINE] Passing {len(all_image_paths)} image(s) to TripoSR: {[os.path.basename(p) for p in all_image_paths]}")
                results = lts.generate_3d(all_image_paths, models_dir, asset_slug)
                method_used = "local_triposr_gpu"
            except Exception as e:
                print(f"[PIPELINE] Local TripoSR GPU failed: {e}")
                return jsonify({
                    "success": False,
                    "error": f"TripoSR GPU thất bại: {str(e)}. Hãy thử phương pháp CLIP Template hoặc kiểm tra GPU."
                }), 500
        else:
            return jsonify({
                "success": False,
                "error": "TripoSR GPU không khả dụng (thiếu weights hoặc CUDA). Hãy chọn CLIP Template."
            }), 500

    elif asset_style == 'template_retrieval':
        try:
            print("[PIPELINE] Running Template Retrieval + Deformation...")
            ts = get_template_service()
            if ts and ts.is_available():
                from PIL import Image
                no_bg_pil = Image.open(no_bg_abs_path).convert('RGBA')
                results = ts.generate_3d(
                    no_bg_image=no_bg_pil,
                    no_bg_path=no_bg_abs_path,
                    additional_views=additional_abs,
                    models_dir=models_dir,
                    asset_slug=asset_slug
                )
                method_used = "template_retrieval"
            else:
                return jsonify({
                    "success": False,
                    "error": "CLIP Template không khả dụng (thiếu dependencies). Hãy chọn TripoSR GPU."
                }), 500
        except Exception as e:
            print(f"[PIPELINE] Template Retrieval failed: {e}")
            return jsonify({
                "success": False,
                "error": f"CLIP Template thất bại: {str(e)}. Hãy thử TripoSR GPU."
            }), 500

    else:
        return jsonify({
            "success": False,
            "error": f"Phương pháp '{asset_style}' không hợp lệ. Chỉ chấp nhận template_retrieval hoặc local_triposr_gpu."
        }), 400

    if results is None:
        return jsonify({
            "success": False,
            "error": "Không có phương pháp sinh 3D nào được chọn."
        }), 400

    glb_rel = f"/static/models/{asset_slug}.glb"
    obj_rel = f"/static/models/{asset_slug}.obj"
    ply_rel = f"/static/models/{asset_slug}.ply"

    sql = """
        UPDATE assets 
        SET model_glb = %s, model_obj = %s, model_ply = %s, 
            vertices = %s, faces = %s, texture_size = %s, 
            file_size = %s, inference_time = %s
        WHERE id = %s
    """
    db_service.execute(sql, (
        glb_rel, obj_rel, ply_rel,
        results.get('vertices', 0),
        results.get('faces', 0),
        results.get('texture_size', 'N/A'),
        results.get('file_size', '0 MB'),
        results.get('inference_time', 0),
        asset_id
    ))

    return jsonify({
        "success": True,
        "asset_id": asset_id,
        "method": method_used,
        "original_image": asset['original_image'],
        "no_bg_image": asset['no_bg_image'],
        "metrics": {
            "vertices": results.get('vertices', 0),
            "faces": results.get('faces', 0),
            "texture_size": results.get('texture_size', 'N/A'),
            "file_size": results.get('file_size', '0 MB'),
            "inference_time": results.get('inference_time', 0)
        },
        "models": {
            "glb": glb_rel,
            "obj": obj_rel,
            "ply": ply_rel
        }
    })


@api_bp.route('/api/templates', methods=['GET'])
def get_templates():
    """Lists all curated templates from the template metadata database."""
    try:
        import sqlite3
        db_path = os.path.join(current_app.root_path, 'data', 'template_metadata.sqlite')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT uid, faiss_idx, name, category, glb_path, vertices, faces, dataset "
            "FROM templates ORDER BY name"
        ).fetchall()
        conn.close()

        thumb_dir = os.path.join(current_app.root_path, 'docs', 'template_catalog', 'thumbnails')
        templates = []
        for r in rows:
            uid = r['uid']
            d = dict(r)
            d['has_thumbnail'] = os.path.exists(os.path.join(thumb_dir, f"{uid}.png"))
            glb = d.get('glb_path') or ''
            abs_path = os.path.join(current_app.root_path, glb.lstrip('/').replace('\\\\', '/').replace('\\', '/').replace('/', os.sep)) if glb else ''
            d['size_mb'] = round(os.path.getsize(abs_path) / (1024 * 1024), 2) if abs_path and os.path.exists(abs_path) else 0
            templates.append(d)

        return jsonify({"success": True, "count": len(templates), "templates": templates})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route('/api/templates/<uid>/thumbnail', methods=['GET'])
def get_template_thumbnail(uid):
    """Serves a template thumbnail PNG if available, otherwise a placeholder."""
    thumb_path = os.path.join(
        current_app.root_path, 'docs', 'template_catalog', 'thumbnails', f"{uid}.png"
    )
    if os.path.exists(thumb_path):
        return send_from_directory(
            os.path.dirname(thumb_path),
            os.path.basename(thumb_path),
            mimetype='image/png'
        )
    # Placeholder
    try:
        from PIL import Image
        buf = io.BytesIO()
        img = Image.new('RGB', (300, 300), (26, 32, 44))
        img.save(buf, format='PNG')
        buf.seek(0)
        return send_file(buf, mimetype='image/png')
    except Exception:
        return '', 404


@api_bp.route('/api/templates/<uid>/import', methods=['POST'])
def import_template(uid):
    """Copies a curated template GLB into the user's asset library as a usable 3D asset."""
    try:
        import sqlite3
        db_path = os.path.join(current_app.root_path, 'data', 'template_metadata.sqlite')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM templates WHERE uid = ?", (uid,)).fetchone()
        conn.close()
        if not row:
            return jsonify({"error": "Template not found"}), 404

        src_rel = (row['glb_path'] or '').replace('\\\\', '/').replace('\\', '/')
        src_abs = os.path.join(current_app.root_path, src_rel.lstrip('/').replace('/', os.sep))
        if not os.path.exists(src_abs):
            return jsonify({"error": "Template GLB file missing on disk"}), 500

        # Copy into static/models so deleting the asset never touches the template file
        models_dir = os.path.join(current_app.root_path, 'static', 'models')
        os.makedirs(models_dir, exist_ok=True)
        target_name = f"tpl_{uid}.glb"
        target_abs = os.path.join(models_dir, target_name)
        with open(src_abs, 'rb') as fsrc, open(target_abs, 'wb') as fdst:
            fdst.write(fsrc.read())

        size = os.path.getsize(target_abs)
        glb_rel = f"/static/models/{target_name}"

        sql = """
            INSERT INTO assets (name, original_image, additional_images, no_bg_image, model_glb, model_obj, model_ply, file_size, style)
            VALUES (%s, %s, %s, '', %s, '', '', %s, 'template_retrieval')
        """
        asset_id = db_service.execute(sql, (
            row['name'], '/static/img/template_placeholder.png', '[]',
            glb_rel, f"{size / (1024 * 1024):.2f} MB"
        ))

        return jsonify({
            "success": True,
            "asset_id": asset_id,
            "message": f"Đã nhập khuôn mẫu '{row['name']}' vào Thư Viện Asset."
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route('/api/assets', methods=['GET'])
def get_assets():
    """Lists all assets from database with optional searching/filtering."""
    search = request.args.get('search', '').strip()
    
    if search:
        sql = "SELECT * FROM assets WHERE name LIKE %s ORDER BY created_at DESC"
        assets = db_service.query(sql, (f"%{search}%",))
    else:
        sql = "SELECT * FROM assets ORDER BY created_at DESC"
        assets = db_service.query(sql)
        
    return jsonify({
        "success": True,
        "count": len(assets),
        "assets": assets
    })


@api_bp.route('/api/assets/<int:asset_id>', methods=['GET'])
def get_asset_by_id(asset_id):
    """Retrieves a single asset by its ID."""
    asset = db_service.query("SELECT * FROM assets WHERE id = %s", (asset_id,), fetchone=True)
    if not asset:
        return jsonify({"error": "Asset not found"}), 404
        
    return jsonify({
        "success": True,
        "asset": asset
    })


@api_bp.route('/api/assets/<int:asset_id>', methods=['DELETE'])
def delete_asset(asset_id):
    """Deletes an asset from database and removes its local files."""
    asset = db_service.query("SELECT * FROM assets WHERE id = %s", (asset_id,), fetchone=True)
    if not asset:
        return jsonify({"error": "Asset not found"}), 404
        
    # Delete local files if they exist
    files_to_delete = [
        asset.get('original_image'),
        asset.get('no_bg_image'),
        asset.get('model_glb'),
        asset.get('model_obj'),
        asset.get('model_ply')
    ]
    
    # Also delete the associated .mtl file which accompanies OBJ
    if asset.get('model_obj'):
        files_to_delete.append(asset['model_obj'].replace('.obj', '.mtl'))
        
    for f in files_to_delete:
        if f:
            abs_path = os.path.join(current_app.root_path, f.lstrip('/'))
            if os.path.exists(abs_path):
                try:
                    os.remove(abs_path)
                except Exception as e:
                    print(f"[API Error] Failed to delete file {abs_path}: {e}")
                    
    # Delete from DB
    db_service.execute("DELETE FROM assets WHERE id = %s", (asset_id,))
    
    return jsonify({
        "success": True,
        "message": f"Asset {asset_id} deleted successfully."
    })


@api_bp.route('/api/assets/<int:asset_id>/editor-save', methods=['POST'])
def editor_save(asset_id):
    data = request.json or {}
    editor_state = data.get('editor_state')
    if editor_state is None:
        return jsonify({"error": "Missing editor_state"}), 400
    editor_state_json = json.dumps(editor_state)
    db_service.execute("UPDATE assets SET editor_state = %s WHERE id = %s", (editor_state_json, asset_id))
    return jsonify({"success": True})


@api_bp.route('/api/assets/<int:asset_id>/editor-load', methods=['GET'])
def editor_load(asset_id):
    asset = db_service.query("SELECT editor_state FROM assets WHERE id = %s", (asset_id,), fetchone=True)
    if not asset:
        return jsonify({"error": "Asset not found"}), 404
    raw = asset.get('editor_state')
    if raw is None:
        return jsonify({"success": True, "editor_state": None})
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return jsonify({"success": True, "editor_state": parsed})
        except json.JSONDecodeError:
            return jsonify({"success": True, "editor_state": raw})
    return jsonify({"success": True, "editor_state": raw})


@api_bp.route('/api/assets/<int:asset_id>/export-edited', methods=['POST'])
def export_edited(asset_id):
    data = request.json or {}
    glb_b64 = data.get('glb_data')
    if not glb_b64:
        return jsonify({"error": "Missing glb_data"}), 400

    asset = db_service.query("SELECT * FROM assets WHERE id = %s", (asset_id,), fetchone=True)
    if not asset:
        return jsonify({"error": "Asset not found"}), 404

    current_glb = asset.get('model_glb', '')
    # Derive slug from existing glb path or fall back to model_{asset_id}
    if current_glb:
        basename = os.path.basename(current_glb)
        slug = basename.replace('.glb', '')
    else:
        slug = f"model_{asset_id}"

    edited_filename = f"{slug}_edited.glb"
    models_dir = os.path.join(current_app.root_path, 'static', 'models')
    os.makedirs(models_dir, exist_ok=True)
    edited_path = os.path.join(models_dir, edited_filename)

    try:
        glb_bytes = base64.b64decode(glb_b64)
        with open(edited_path, 'wb') as f:
            f.write(glb_bytes)
    except Exception as e:
        return jsonify({"error": f"Failed to decode/save GLB: {str(e)}"}), 500

    glb_rel = f"/static/models/{edited_filename}"
    db_service.execute("UPDATE assets SET model_glb = %s WHERE id = %s", (glb_rel, asset_id))

    return jsonify({"success": True, "glb_path": glb_rel})
