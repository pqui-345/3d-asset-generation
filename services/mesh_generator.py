"""
3D Mesh Generator - Multi-view Elliptical Engine v6
Creates 3D meshes with elliptical cross-sections from front + side views.
Approach: Front profile (width) + Side profile (depth) = Elliptical mesh
"""
import os, time, struct, json, math, shutil
from PIL import Image

def _extract_profile(img_path, G=120):
    """Extract width profile from an image: returns [(norm_height, width), ...]"""
    img = Image.open(img_path).convert("RGBA")
    ir = img.resize((G, G), Image.Resampling.LANCZOS)
    px = ir.load()
    mask = [[False]*G for _ in range(G)]
    mnx, mxx, mny, mxy = G, 0, G, 0
    for y in range(G):
        for x in range(G):
            _, _, _, a = px[x, y]
            if a > 20:
                mask[y][x] = True
                mnx, mxx = min(mnx, x), max(mxx, x)
                mny, mxy = min(mny, y), max(mxy, y)
    if mxx <= mnx or mxy <= mny:
        return None

    ow = mxx - mnx + 1
    oh = mxy - mny + 1
    profile = []
    for y in range(G):
        left = -1
        right = -1
        for x in range(G):
            if mask[y][x]:
                if left < 0: left = x
                right = x
        if left >= 0:
            nh = (y - mny) / oh
            w = (right - left) / ow
            profile.append((max(0, min(1, nh)), w))
    if not profile:
        return None

    # Sort by height and smooth
    profile.sort(key=lambda p: p[0])
    for _ in range(3):
        tmp = list(profile)
        for i in range(1, len(profile)-1):
            n = [profile[j][1] for j in range(i-1, i+2) if profile[j][1] > 0.01]
            if n:
                tmp[i] = (profile[i][0], sum(n)/len(n))
        profile = tmp
    return profile


def _generate_normal_map(img_path, output_normal_path):
    """Generate Normal Map from image using Sobel filters."""
    try:
        from PIL import Image, ImageFilter
        import numpy as np
        img = Image.open(img_path).convert("RGBA")
        r, g, b, a = img.split()
        gray = img.convert("L")
        
        # Apply a minor Gaussian blur to smooth high frequency noise
        gray_smooth = gray.filter(ImageFilter.GaussianBlur(1.0))
        img_np = np.array(gray_smooth, dtype=np.float32)
        
        # Sobel filters for gradients
        dy, dx = np.gradient(img_np)
        
        # Control normal map depth strength
        strength = 4.0
        
        # Calculate normal vectors
        nx = -dx * strength
        ny = -dy * strength  # Invert Y to match typical OpenGL coordinate systems
        nz = np.ones_like(img_np) * 255.0
        
        # Normalize vectors to unit length
        norm = np.sqrt(nx**2 + ny**2 + nz**2)
        # Avoid division by zero
        norm = np.where(norm < 1e-6, 1.0, norm)
        nx = (nx / norm * 0.5 + 0.5) * 255.0
        ny = (ny / norm * 0.5 + 0.5) * 255.0
        nz = (nz / norm * 0.5 + 0.5) * 255.0
        
        # Stack channels to RGB
        normal_rgb = np.stack([nx, ny, nz], axis=-1).astype(np.uint8)
        
        # Mask background areas to neutral normal color (128, 128, 255)
        a_np = np.array(a)
        mask = a_np < 20
        normal_rgb[mask] = [128, 128, 255]
        
        normal_img = Image.fromarray(normal_rgb, "RGB")
        normal_img.save(output_normal_path, "PNG")
        print(f"[MeshGen] Normal map generated successfully at: {output_normal_path}")
        return True
    except Exception as e:
        print(f"[MeshGen] Error generating normal map: {e}")
        return False


class MeshGeneratorService:

    @staticmethod
    def generate_extruded_silhouette(no_bg_image_path, output_dir, asset_name):
        # Nâng cấp Strategy 3: Sử dụng Depth Estimation thay vì đùn phẳng (Flat Extrusion)
        # Tạo mô hình phù điêu (Relief Surface) 2.5D chân thực hơn
        t0 = time.time()
        glb_f = f"{asset_name}.glb"
        glb_p = os.path.join(output_dir, glb_f)

        if not os.path.exists(no_bg_image_path):
            raise FileNotFoundError("Image not found.")

        import numpy as np
        import trimesh
        import torch
        from transformers import pipeline

        print("[MeshGen] Step 1: Loading image and running Depth Estimation...")
        img = Image.open(no_bg_image_path).convert("RGBA")
        
        try:
            pipe = pipeline("depth-estimation", model="Intel/dpt-large", device=0 if torch.cuda.is_available() else -1)
            depth_res = pipe(img)
            depth_img = depth_res['depth']
        except Exception as e:
            print(f"[MeshGen] Depth estimation failed: {e}. Falling back to flat depth.")
            depth_img = Image.new("L", img.size, 128)

        # Scale down to 256x256 for mesh generation to keep polycount reasonable (~130k triangles)
        G = 256
        img_rs = img.resize((G, G), Image.Resampling.LANCZOS)
        depth_rs = depth_img.resize((G, G), Image.Resampling.LANCZOS)
        
        img_np = np.array(img_rs)
        depth_np = np.array(depth_rs, dtype=np.float32)
        
        d_min, d_max = depth_np.min(), depth_np.max()
        if d_max > d_min:
            depth_np = (depth_np - d_min) / (d_max - d_min)
        else:
            depth_np = np.zeros_like(depth_np)
            
        mask = img_np[:, :, 3] > 120
        
        print("[MeshGen] Step 2: Building 2.5D Relief Mesh (Front & Back)...")
        SCALE = 2.0
        DEPTH_SCALE = 0.3
        
        verts = []
        colors = []
        vertex_map_front = {}
        vertex_map_back = {}
        
        # Create Front Vertices (Displaced by Depth)
        for y in range(G):
            for x in range(G):
                if mask[y, x]:
                    vx = (x / G - 0.5) * SCALE
                    vy = (0.5 - y / G) * SCALE
                    vz = depth_np[y, x] * DEPTH_SCALE
                    
                    idx = len(verts)
                    verts.append([vx, vy, vz])
                    colors.append(img_np[y, x])
                    vertex_map_front[(x, y)] = idx
                    
        # Create Back Vertices (Flat at Z = -DEPTH_SCALE/2)
        back_z = -DEPTH_SCALE * 0.5
        for y in range(G):
            for x in range(G):
                if mask[y, x]:
                    vx = (x / G - 0.5) * SCALE
                    vy = (0.5 - y / G) * SCALE
                    
                    idx = len(verts)
                    verts.append([vx, vy, back_z])
                    colors.append(img_np[y, x])
                    vertex_map_back[(x, y)] = idx

        faces = []
        # Triangulate Front and Back Faces
        for y in range(G - 1):
            for x in range(G - 1):
                if mask[y, x] and mask[y, x+1] and mask[y+1, x] and mask[y+1, x+1]:
                    # Front quad
                    f1, f2, f3, f4 = vertex_map_front[(x,y)], vertex_map_front[(x+1,y)], vertex_map_front[(x+1,y+1)], vertex_map_front[(x,y+1)]
                    faces.append([f1, f4, f2])
                    faces.append([f2, f4, f3])
                    # Back quad (inverted winding)
                    b1, b2, b3, b4 = vertex_map_back[(x,y)], vertex_map_back[(x+1,y)], vertex_map_back[(x+1,y+1)], vertex_map_back[(x,y+1)]
                    faces.append([b1, b2, b4])
                    faces.append([b2, b3, b4])

        # Watertight boundary wall stitching
        print("[MeshGen] Step 2b: Stitching boundary walls for watertight model...")
        for y in range(G - 1):
            for x in range(G - 1):
                # Edge 1: Vertical boundary between (x, y) and (x+1, y)
                if mask[y, x] != mask[y, x+1]:
                    # Check if this edge continues to y+1
                    if mask[y+1, x] != mask[y+1, x+1]:
                        # If the mask values match (both solid on left, or both on right)
                        if mask[y, x] == mask[y+1, x]:
                            # Determine which is solid
                            if mask[y, x]: # Solid on left: (x, y) and (x, y+1)
                                v_f1 = vertex_map_front[(x, y)]
                                v_b1 = vertex_map_back[(x, y)]
                                v_b2 = vertex_map_back[(x, y+1)]
                                v_f2 = vertex_map_front[(x, y+1)]
                                # CCW facing right (+X)
                                faces.append([v_f1, v_b2, v_b1])
                                faces.append([v_f1, v_f2, v_b2])
                            else: # Solid on right: (x+1, y) and (x+1, y+1)
                                v_f1 = vertex_map_front[(x+1, y)]
                                v_b1 = vertex_map_back[(x+1, y)]
                                v_b2 = vertex_map_back[(x+1, y+1)]
                                v_f2 = vertex_map_front[(x+1, y+1)]
                                # CCW facing left (-X)
                                faces.append([v_f1, v_b1, v_b2])
                                faces.append([v_f1, v_b2, v_f2])

                # Edge 2: Horizontal boundary between (x, y) and (x, y+1)
                if mask[y, x] != mask[y+1, x]:
                    # Check if this edge continues to x+1
                    if mask[y, x+1] != mask[y+1, x+1]:
                        # If the mask values match (both solid on top, or both on bottom)
                        if mask[y, x] == mask[y, x+1]:
                            if mask[y, x]: # Solid on top: (x, y) and (x+1, y)
                                v_f1 = vertex_map_front[(x, y)]
                                v_b1 = vertex_map_back[(x, y)]
                                v_b2 = vertex_map_back[(x+1, y)]
                                v_f2 = vertex_map_front[(x+1, y)]
                                # CCW facing down (-Y)
                                faces.append([v_f1, v_b1, v_b2])
                                faces.append([v_f1, v_b2, v_f2])
                            else: # Solid on bottom: (x, y+1) and (x+1, y+1)
                                v_f1 = vertex_map_front[(x, y+1)]
                                v_b1 = vertex_map_back[(x, y+1)]
                                v_b2 = vertex_map_back[(x+1, y+1)]
                                v_f2 = vertex_map_front[(x+1, y+1)]
                                # CCW facing up (+Y)
                                faces.append([v_f1, v_b2, v_b1])
                                faces.append([v_f1, v_f2, v_b2])

        print("[MeshGen] Step 3: Exporting Relief GLB...")
        verts = np.array(verts, dtype=np.float32)
        faces = np.array(faces, dtype=np.int32)
        colors = np.array(colors, dtype=np.uint8)

        mesh = trimesh.Trimesh(vertices=verts, faces=faces, vertex_colors=colors, process=False)
        # Flip orientation for Three.js
        mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [1, 0, 0]))
        
        mesh.export(glb_p)
        
        it = round(time.time() - t0, 3)
        fs = os.path.getsize(glb_p)

        return {
            "method": "procedural_relief_2.5d",
            "name": asset_name,
            "vertices": len(verts),
            "faces": len(faces),
            "file_size": f"{fs/(1024*1024):.2f} MB",
            "inference_time": it,
            "glb_path": f"/static/models/{glb_f}"
        }

    @staticmethod
    def generate_3d_model(no_bg_image_path, output_dir, asset_name, additional_views=None, style='extruded'):
        if style == 'extruded':
            return MeshGeneratorService.generate_extruded_silhouette(no_bg_image_path, output_dir, asset_name)
        
        t0 = time.time()

        glb_f = f"{asset_name}.glb"
        obj_f = f"{asset_name}.obj"
        ply_f = f"{asset_name}.ply"
        mtl_f = f"{asset_name}.mtl"
        normal_f = f"{asset_name}_normal.png"
        glb_p = os.path.join(output_dir, glb_f)
        obj_p = os.path.join(output_dir, obj_f)
        ply_p = os.path.join(output_dir, ply_f)
        mtl_p = os.path.join(output_dir, mtl_f)
        normal_p = os.path.join(output_dir, normal_f)

        if not os.path.exists(no_bg_image_path):
            raise FileNotFoundError("Image not found.")

        # Generate normal map
        _generate_normal_map(no_bg_image_path, normal_p)

        img = Image.open(no_bg_image_path).convert("RGBA")
        W, H = img.size

        # Fill transparent areas with solid color (nearest neighbor) to avoid holes in 3D mesh
        img_filled = img.copy()
        px_filled = img_filled.load()
        for fy in range(H):
            for fx in range(W):
                r, g, b, a = px_filled[fx, fy]
                if a < 128:
                    # Search nearest non-transparent pixel
                    found = False
                    for sr in range(1, 20):
                        for sy in range(-sr, sr+1):
                            for sx in range(-sr, sr+1):
                                ny, nx = fy+sy, fx+sx
                                if 0 <= nx < W and 0 <= ny < H:
                                    _, _, _, na = px_filled[nx, ny]
                                    if na > 128:
                                        nr, ng, nb, _ = px_filled[nx, ny]
                                        px_filled[fx, fy] = (nr, ng, nb, 255)
                                        found = True
                                        break
                            if found: break
                        if found: break
                    if not found:
                        px_filled[fx, fy] = (200, 200, 200, 255)
        filled_path = no_bg_image_path.replace('.png', '_filled.png').replace('.jpg', '_filled.png')
        img_filled.save(filled_path)
        bn = os.path.basename(filled_path)

        # Copy filled texture to models dir
        cp_filled = os.path.join(output_dir, bn)
        if filled_path != cp_filled:
            shutil.copy2(filled_path, cp_filled)

        # Use filled image for profile extraction
        img = img_filled

        # === Extract front (width) profile from primary image ===
        front_profile = _extract_profile(filled_path)
        if not front_profile or len(front_profile) < 4:
            raise Exception("Cannot extract front profile")

        # Load luminance map for surface detail (from filled image)
        detail_img = Image.open(filled_path).convert("RGBA")
        detail_ir = detail_img.resize((256, 256), Image.Resampling.LANCZOS)
        detail_px = detail_ir.load()
        lum_map = [[0.0]*256 for _ in range(256)]
        for dy in range(256):
            for dx in range(256):
                r, g, b, a = detail_px[dx, dy]
                lum_map[dy][dx] = (0.299*r + 0.587*g + 0.114*b) / 255.0 if a > 20 else 0.5

        # === Extract side (depth) profile from additional views ===
        side_profile = None
        if additional_views:
            for vp in additional_views:
                if os.path.exists(vp):
                    sp = _extract_profile(vp)
                    if sp and len(sp) >= 4:
                        side_profile = sp
                        print(f"[MeshGen] Side profile: {os.path.basename(vp)} ({len(sp)} pts)")
                        break

        # Merge profiles: at each height, width from front, depth from side
        # If no side view, depth = width (circular)
        merged = []
        for nh, w in front_profile:
            d = w  # default: circular
            if side_profile:
                # Find matching height in side profile
                for snh, sw in side_profile:
                    if abs(snh - nh) < 0.05:
                        d = max(w * 0.3, sw)
                        break
            merged.append((nh, w, d))

        # Interpolate to fixed number of rings
        RINGS = 64
        SEGMENTS = 48
        SCALE = 1.8

        heights = [i / (RINGS - 1) for i in range(RINGS)]
        interp = []
        for nh in heights:
            # Find nearest values in merged
            below, above = None, None
            for mnh, mw, md in merged:
                if mnh <= nh:
                    below = (mnh, mw, md)
                if mnh >= nh and above is None:
                    above = (mnh, mw, md)
            if below is None:
                below = above
            if above is None:
                above = below
            if below == above:
                w, d = below[1], below[2]
            else:
                t = (nh - below[0]) / max(above[0] - below[0], 0.001)
                w = below[1] + t * (above[1] - below[1])
                d = below[2] + t * (above[2] - below[2])
            interp.append((nh, w * 0.5, d * 0.5))

        # Build mesh with elliptical cross-sections + luminance displacement
        DISP_STRENGTH = 0.04
        verts = []
        uv_list = []
        faces = []
        add_center_top = None
        add_center_bot = None

        for ri, (nh, rx, ry) in enumerate(interp):
            z = (nh - 0.5) * SCALE * 1.2
            for si in range(SEGMENTS):
                angle = 2.0 * math.pi * si / SEGMENTS
                frontness = math.cos(angle)
                u = 0.5 + 0.5 * frontness
                v = 1.0 - nh
                # Sample luminance for displacement
                lx = min(255, max(0, int(u * 255)))
                ly = min(255, max(0, int(v * 255)))
                lval = lum_map[ly][lx]
                disp = (lval - 0.5) * DISP_STRENGTH * SCALE
                base_x = rx * SCALE * math.cos(angle)
                base_y = ry * SCALE * math.sin(angle)
                # Displace along radial direction
                dist = math.sqrt(base_x*base_x + base_y*base_y)
                if dist > 0.001:
                    x = base_x + (base_x / dist) * disp
                    y = base_y + (base_y / dist) * disp
                else:
                    x, y = base_x, base_y
                verts.append((x, z, y))
                uv_list.append((max(0, min(1, u)), max(0, min(1, v))))

        # Center vertices for caps
        top_z = (1.0 - 0.5) * SCALE * 1.2
        bot_z = (0.0 - 0.5) * SCALE * 1.2
        top_idx = len(verts)
        verts.append((0, top_z, 0))
        uv_list.append((0.5, 0.0))
        bot_idx = len(verts)
        verts.append((0, bot_z, 0))
        uv_list.append((0.5, 1.0))

        # Side faces
        for ri in range(RINGS - 1):
            i0 = ri * SEGMENTS
            i1 = (ri + 1) * SEGMENTS
            for si in range(SEGMENTS):
                sn = (si + 1) % SEGMENTS
                v00 = i0 + si
                v01 = i0 + sn
                v10 = i1 + si
                v11 = i1 + sn
                if all(v < len(verts) for v in (v00, v01, v10, v11)):
                    faces.append((v00, v10, v01))
                    faces.append((v01, v10, v11))

        # Top cap
        if interp[-1][1] > 0.01 or interp[-1][2] > 0.01:
            last_ring = (RINGS - 1) * SEGMENTS
            for si in range(SEGMENTS):
                sn = (si + 1) % SEGMENTS
                v = last_ring + si
                vn = last_ring + sn
                if v < len(verts) and vn < len(verts):
                    faces.append((v, vn, top_idx))

        # Bottom cap
        if interp[0][1] > 0.01 or interp[0][2] > 0.01:
            for si in range(SEGMENTS):
                sn = (si + 1) % SEGMENTS
                v = si
                vn = sn
                if v < len(verts) and vn < len(verts):
                    faces.append((v, bot_idx, vn))

        # Clean degenerate faces
        nv = len(verts)
        valid = []
        seen = set()
        for f in faces:
            if f[0] == f[1] or f[1] == f[2] or f[0] == f[2]:
                continue
            if any(v >= nv for v in f):
                continue
            k = tuple(sorted(f))
            if k not in seen:
                seen.add(k)
                valid.append(f)
        faces = valid

        # Smooth normals
        acc = [[0.0, 0.0, 0.0] for _ in range(nv)]
        for f in faces:
            i0, i1, i2 = f
            v0, v1, v2 = verts[i0], verts[i1], verts[i2]
            e1 = (v1[0]-v0[0], v1[1]-v0[1], v1[2]-v0[2])
            e2 = (v2[0]-v0[0], v2[1]-v0[1], v2[2]-v0[2])
            fn = (e1[1]*e2[2]-e1[2]*e2[1],
                  e1[2]*e2[0]-e1[0]*e2[2],
                  e1[0]*e2[1]-e1[1]*e2[0])
            fl = math.sqrt(fn[0]**2+fn[1]**2+fn[2]**2)
            if fl > 0:
                fn = (fn[0]/fl, fn[1]/fl, fn[2]/fl)
                for i in (i0, i1, i2):
                    acc[i][0] += fn[0]
                    acc[i][1] += fn[1]
                    acc[i][2] += fn[2]
        normals = []
        for a in acc:
            l = math.sqrt(a[0]**2+a[1]**2+a[2]**2)
            normals.append((a[0]/l, a[1]/l, a[2]/l) if l > 1e-6 else (0, 0, 1))

        # Write OBJ
        with open(mtl_p, "w") as f:
            f.write(f"newmtl material_0\nKa 1 1 1\nKd 1 1 1\nKs 0.5 0.5 0.5\nNs 120\nmap_Kd {bn}\nbump {normal_f}\nmap_Kn {normal_f}\n")
        with open(obj_p, "w") as f:
            f.write(f"mtllib {mtl_f}\ng {asset_name}\n\n")
            for v in verts:
                f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            f.write("\n")
            for u in uv_list:
                f.write(f"vt {u[0]:.6f} {u[1]:.6f}\n")
            f.write("\n")
            for n in normals:
                f.write(f"vn {n[0]:.6f} {n[1]:.6f} {n[2]:.6f}\n")
            f.write(f"\nusemtl material_0\n")
            for fc in faces:
                f.write(f"f {fc[0]+1}/{fc[0]+1}/{fc[0]+1} {fc[1]+1}/{fc[1]+1}/{fc[1]+1} {fc[2]+1}/{fc[2]+1}/{fc[2]+1}\n")

        # Write PLY
        with open(ply_p, "w") as f:
            f.write("ply\nformat ascii 1.0\n")
            f.write(f"element vertex {nv}\nproperty float x\nproperty float y\nproperty float z\n")
            f.write("property float nx\nproperty float ny\nproperty float nz\n")
            f.write(f"element face {len(faces)}\nproperty list uchar int vertex_indices\nend_header\n")
            for i, v in enumerate(verts):
                n = normals[i]
                f.write(f"{v[0]:.6f} {v[1]:.6f} {v[2]:.6f} {n[0]:.6f} {n[1]:.6f} {n[2]:.6f}\n")
            for fc in faces:
                f.write(f"3 {fc[0]} {fc[1]} {fc[2]}\n")

        # Write GLB (use filled texture and normal map)
        with open(glb_p, "wb") as fg:
            fg.write(GLBExporter.export(verts, faces, uv_list, normals, filled_path, normal_p))

        it = round(time.time() - t0, 3)
        fs = sum(os.path.getsize(p) for p in [obj_p, glb_p] if os.path.exists(p))

        return {
            "method": "procedural_elliptical",
            "name": asset_name,
            "vertices": nv,
            "faces": len(faces),
            "texture_size": f"{W}x{H} px",
            "file_size": f"{fs/(1024*1024):.2f} MB",
            "inference_time": it,
            "glb_path": f"/static/models/{glb_f}",
            "obj_path": f"/static/models/{obj_f}",
            "ply_path": f"/static/models/{ply_f}",
            "mtl_path": f"/static/models/{mtl_f}"
        }


class GLBExporter:
    @staticmethod
    def export(verts, faces, uvs, normals, tex_path, normal_tex_path=None):
        with open(tex_path, "rb") as f:
            tex = f.read()
        while len(tex) % 4 != 0:
            tex += b"\x00"

        has_normal = False
        normal_tex = b""
        if normal_tex_path and os.path.exists(normal_tex_path):
            try:
                with open(normal_tex_path, "rb") as f:
                    normal_tex = f.read()
                while len(normal_tex) % 4 != 0:
                    normal_tex += b"\x00"
                has_normal = True
            except Exception as e:
                print(f"[GLBExporter] Error reading normal map: {e}")

        S = 32
        vb = bytearray()
        mn, mx = [float('inf')]*3, [float('-inf')]*3
        for i, v in enumerate(verts):
            n, u = normals[i], uvs[i]
            vb += struct.pack("<8f", v[0], v[1], v[2], n[0], n[1], n[2], u[0], u[1])
            for j in range(3):
                mn[j] = min(mn[j], v[j])
                mx[j] = max(mx[j], v[j])
        while len(vb) % 4:
            vb += b"\x00"

        ib = bytearray()
        for fc in faces:
            ib += struct.pack("<HHH", fc[0], fc[1], fc[2])
        while len(ib) % 4:
            ib += b"\x00"

        vl, il, tl, ntl = len(vb), len(ib), len(tex), len(normal_tex)
        total = vl + il + tl + ntl

        gj = {
            "asset": {"version": "2.0", "generator": "3DGame Elliptical v6"},
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes": [{"mesh": 0, "name": "Asset"}],
            "meshes": [{"primitives": [{"attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2}, "indices": 3, "material": 0}]}],
            "materials": [{
                "name": "Mat",
                "alphaMode": "BLEND",
                "doubleSided": True,
                "pbrMetallicRoughness": {
                    "baseColorTexture": {"index": 0},
                    "metallicFactor": 0.05,
                    "roughnessFactor": 0.45
                }
            }],
            "textures": [{"source": 0, "sampler": 0}],
            "images": [{"bufferView": 2, "mimeType": "image/png"}],
            "samplers": [{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}],
            "bufferViews": [
                {"buffer": 0, "byteOffset": 0, "byteLength": vl, "byteStride": S, "target": 34962},
                {"buffer": 0, "byteOffset": vl, "byteLength": il, "target": 34963},
                {"buffer": 0, "byteOffset": vl+il, "byteLength": tl}
            ],
            "accessors": [
                {"bufferView": 0, "byteOffset": 0, "componentType": 5126, "count": len(verts), "type": "VEC3", "min": mn, "max": mx},
                {"bufferView": 0, "byteOffset": 12, "componentType": 5126, "count": len(verts), "type": "VEC3"},
                {"bufferView": 0, "byteOffset": 24, "componentType": 5126, "count": len(verts), "type": "VEC2"},
                {"bufferView": 1, "byteOffset": 0, "componentType": 5123, "count": len(faces)*3, "type": "SCALAR"}
            ],
            "buffers": [{"byteLength": total}]
        }

        if has_normal:
            gj["textures"].append({"source": 1, "sampler": 0})
            gj["images"].append({"bufferView": 3, "mimeType": "image/png"})
            gj["bufferViews"].append({"buffer": 0, "byteOffset": vl+il+tl, "byteLength": ntl})
            gj["materials"][0]["normalTexture"] = {"index": 1, "scale": 1.5}

        jb = bytearray(json.dumps(gj, separators=(',', ':')).encode('utf-8'))
        while len(jb) % 4:
            jb += b" "
        tg = 12 + 8 + len(jb) + 8 + total
        return (struct.pack("<III", 0x46546C67, 2, tg)
                + struct.pack("<II", len(jb), 0x4E4F534A) + jb
                + struct.pack("<II", total, 0x004E4942) + vb + ib + tex + normal_tex)
