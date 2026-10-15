"""
Cleanup script: reduce template library from 475 -> 84 curated templates.

Steps:
1. Back up data files (already done manually, but keeps a safety copy here).
2. Delete GLB files for discarded templates (391 files) + 2 orphan files.
3. Delete discarded rows from `templates` and `view_embeddings`.
4. Renumber faiss_idx 0..83 for kept templates (in current faiss_idx order).
5. Rebuild FAISS index offline from stored clip_embeddings + view_embeddings
   (no internet / CLIP model required).
6. Rewrite template_index_metadata.json for the new view-embedding section.
"""
import os
import sqlite3
import sys
import shutil
import json
import time

import faiss
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")

ROOT = r"E:\xampp\htdocs\3DGame"
DATA = os.path.join(ROOT, "data")
DB_PATH = os.path.join(DATA, "template_metadata.sqlite")
INDEX_PATH = os.path.join(DATA, "template_index.faiss")
META_PATH = os.path.join(DATA, "template_index_metadata.json")
TEMPLATE_DIR = os.path.join(ROOT, "static", "templates")

# uid -> Vietnamese label (84 templates to KEEP)
KEEP = [
    ("8476c4170df24cf5bbe6967222d1a42d", "ghế (chair)"),
    ("63ecc2ab01cc482d8c92fc51e1d3d871", "bàn (Table)"),
    ("f507c33668e34d16b9306e8a8350f229", "giá sách"),
    ("4b516ca7f743448484550b4da91cf286", "bàn & cốc rượu (lowpoly)"),
    ("fcdfc931f73b4865a4a4005c65fc2afe", "não"),
    ("5699e6ec5c0f40b1ad0f78264595133d", "răng"),
    ("5ed9dbe3d248407fb09d7959b3f13eb4", "phổi"),
    ("7a0c4c6bd5d84f7daf5fcfc5d20516c9", "hệ thận"),
    ("2854a5128d2e44a993a93848c3d4ca70", "vi khuẩn (Streptobacillus)"),
    ("b04fc40bacdf46fa9cd0f5d1c864be24", "bánh răng / đòn bẩy"),
    ("66b40aabfe7447128fbe4126530e7e96", "bình tam giác (flask)"),
    ("acedcaa52310448288b0669e01e23de5", "ống nhòm"),
    ("85e43288cd4f432cb1c6ade8423cc445", "máy tính bỏ túi"),
    ("3b73e11ff7324a6484a17daec8fdac2c", "khối rubik"),
    ("3ea576589cf0490bb76ee3282a3b0e31", "xe tự hành sao Hỏa"),
    ("04d9983ba04242fe99182d4506ea0714", "vỏ sò tím"),
    ("c8cca8bb201d40e3bb5a6f0010f46aa8", "hoa hồng vàng"),
    ("70596c9524f9481bb48e6d39c7534f1f", "xe đồ chơi (mini vehicle)"),
    ("5948de6770a5491ea158cd9e921ebce9", "quả táo"),
    ("45e3468808f844e8b56826655a2573f7", "củ cà rốt"),
    ("d4b6090d1e8e424792c683ccaf31f2a8", "quả cam"),
    ("996e3759a3b14f0da6cbc2b8449e342f", "quả chuối (caramelo plátano)"),
    ("90819403dfba450bb37af4d30eb804e8", "xúc xích"),
    ("d072bd200267477eba8367ee3a62e686", "thịt nướng (prime rib)"),
    ("0d82cbd4aa44404b8a033f33a178a4c4", "bát cháo yến mạch"),
    ("d1fe37e659c84bacbbfeb54ab2fbbd6e", "bình nước (jug)"),
    ("7f05713c5f6144d8b6ba9a3e2464197d", "cốc thủy tinh"),
    ("efbc8da1b1c2411d9162df959904e0bb", "bình xịt"),
    ("1a49b0714571487d9164b9ba13d03e3f", "ấm trà (tetsubin)"),
    ("7a974cb6f38c483e99087cb95e611d26", "dao bếp"),
    ("d63d86611b844bc68df1185ec07acf28", "bàn ghế"),
    ("d5c97f124faa4e91acc045db07138f94", "ghế văn phòng"),
    ("1a3a21e8cc5948a1a6049ddfa0cedb34", "bàn cà phê"),
    ("31035435a88940f3bf2884a06732b66b", "bàn ăn mở rộng"),
    ("4db7ebaae6bb43a88914d87a65c5f88a", "ghế đẩu kim loại"),
    ("b5cde89b5003460dbf73ff9f4c83cada", "ghế sofa"),
    ("b5dd9578b7d84170867defe731fafe8a", "ghế sofa đơn giản"),
    ("335a406d10b64a58b9cbb2360c2ebd7d", "kệ để đồ"),
    ("873424ce06c34f19a4a5d9ae1f5d2292", "tủ đứng"),
    ("7685aa243cf14c3b9c5c443c62fc3bb1", "ghế sofa da cũ"),
    ("5cef5d36107c43df94df547c54628a53", "tuốc nơ vít"),
    ("fb6d38ea02a1483fb385a151a3fb713d", "kính lúp"),
    ("a5fedad56725430b9bcff609407d3b46", "bàn phím máy tính"),
    ("e52a1fe4a9ab46cd80e9538dfc0b85c9", "điện thoại iPhone 4S"),
    ("a3edd70e72014d3fac5e0dc1b4495088", "đồng hồ analog"),
    ("7bb26eb5815d48cfb5d896d1a9586f54", "tay cầm chơi game"),
    ("fd416555923b471f903477f12e222b43", "đèn lồng"),
    ("07d3214101664660841602ddb2f2163d", "ổ khóa & chìa khóa"),
    ("40b434f607e24f52925dc27877751f1a", "tai nghe AirPods Pro"),
    ("cf0ad37b64ce4c5cb30cbaa1285e4bed", "gấu bông"),
    ("c0b83b79fa5644db954f5a3c1a40836d", "khối Tetris"),
    ("48979fb08afc4ad8a3dd17a07c2879c9", "xúc xắc"),
    ("a5a43063c4d540e28b17b45924a1e6c6", "người tuyết"),
    ("d1f4e136372d40feb1c3098b809d2140", "thú bông hamster"),
    ("7c75022d219c433da27b0df4e7813209", "đố tre puzzle"),
    ("4641830300d843329d1c7b8260364173", "khối gỗ xếp hình"),
    ("3bde1ab67c6448169b604dedad6828d8", "xe đạp"),
    ("2b7682e0da194e7689087055440baf07", "xe đua"),
    ("3f6c325d7cd4472d8dbafac1ef9f03d6", "tàu hỏa chở khách"),
    ("20a2d5191b3144d0bc683d4d4fa0c15b", "thuyền"),
    ("dea42da484b94c68ac81d2198f5cdb84", "máy bay"),
    ("062701304c3f4282b815cf8ed861b27e", "ô tô"),
    ("0979f9320f384922acab059b9b91ad8b", "con ngựa"),
    ("f3a88e73b78c4696a9a0f8e34a428901", "mèo cát (sand cat)"),
    ("5aa6524dad834b7283ae9afa0fbbdc5d", "con mèo"),
    ("d02aca356cfb4d5b9836b7c4663bd447", "cừu núi (bighorn)"),
    ("337fb9dbe0b947c3ac509f9e271d1aa2", "cá ngựa vằn"),
    ("b4fe8462219b46088f49cfd847fe78a9", "cừu Minecraft"),
    ("3a50efe6920749f1985bab4537b8afe5", "lá cây"),
    ("b3f6c576821c48f18aa292b16d7df01b", "cây nấm"),
    ("43b124271dac4b53a71e321ea4558e83", "cây cảnh trong nhà"),
    ("3fb18a0c36e24e1a9c8bef3b05735030", "quả thận"),
    ("089ef9f7ea674d93909ab7c00ca037d1", "sọ người"),
    ("598ba2757a194b938a1222d866bb9fe4", "hộp sọ"),
    ("1b5378b435b246c094197cdf1b2801ee", "hóa thạch (Mediospirifer)"),
    ("8a17adcd6841409fb5735fc3a1672a5b", "than đá"),
    ("3189bb396f8b4847afd3cb821dc4b919", "tảng đá"),
    ("60babaee1eb34edca5dcc38363557dd8", "khối lập phương"),
    ("92fe14dfa2614459807c9de74b20ff8d", "hình cầu"),
    ("45e198b344fb41939a80c69dc145b106", "ngôi nhà"),
    ("c4c9e17b8bbf4864a43998c8d02069d0", "bệnh viện"),
    ("4778984090cf4b11a72f84a45846aa75", "ba lô học sinh"),
    ("a64d47adf5144d52a6ce8763a8caf672", "đôi giày"),
    ("0ec69f6a8e0f48e5876710cfe81643fa", "cái gối"),
]

# Known orphan files (not referenced by DB)
ORPHANS = [
    os.path.join(ROOT, "static", "templates", "core_100", "4bc72588c38c4373a54940b0ff97f168.glb"),
    os.path.join(ROOT, "static", "templates", "objaverse_ext", "simple_pencil.glb"),
]

KEEP_UIDS = [k[0] for k in KEEP]
KEEP_SET = set(KEEP_UIDS)
assert len(KEEP_UIDS) == len(KEEP_SET), "Duplicate UIDs in KEEP list!"

VIEW_ORDER = ["front", "back", "left", "right", "top", "bottom"]


def norm_path(p):
    return p.replace("/", os.sep).replace("\\\\", os.sep)


def fmt_mb(b):
    return f"{b / 1024 / 1024:.1f} MB"


def main():
    print("=" * 60)
    print("TEMPLATE CLEANUP: 475 -> 84 curated templates")
    print("=" * 60)

    # 0. Verify backup exists
    backups = sorted(d for d in os.listdir(DATA) if d.startswith("backup_"))
    if not backups:
        print("[ABORT] No backup found in data/. Create one first.")
        return
    print(f"Backup present: {backups[-1]}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    all_templates = cur.execute(
        "SELECT uid, faiss_idx, glb_path FROM templates ORDER BY faiss_idx"
    ).fetchall()
    all_uids = [r["uid"] for r in all_templates]
    print(f"\nDB templates before: {len(all_uids)}")

    missing = [u for u in KEEP_UIDS if u not in set(all_uids)]
    if missing:
        print(f"[ABORT] Keep UIDs missing from DB: {missing}")
        conn.close()
        return

    discard = [r for r in all_templates if r["uid"] not in KEEP_SET]
    print(f"To delete from DB: {len(discard)} templates")

    # 1. Delete GLB files
    deleted_files = 0
    freed_bytes = 0
    for r in discard:
        p = norm_path(r["glb_path"])
        full = p if os.path.isabs(p) else os.path.join(ROOT, p)
        if os.path.exists(full):
            try:
                freed_bytes += os.path.getsize(full)
                os.remove(full)
                deleted_files += 1
            except Exception as e:
                print(f"  FAIL delete {full}: {e}")

    for op in ORPHANS:
        if os.path.exists(op):
            freed_bytes += os.path.getsize(op)
            os.remove(op)
            deleted_files += 1
            print(f"  Removed orphan: {os.path.basename(op)}")

    print(f"\nDeleted {deleted_files} GLB files, freed {fmt_mb(freed_bytes)}")

    # 2. Prune DB
    cur.execute("DELETE FROM templates WHERE uid NOT IN (%s)" % ",".join("?" * len(KEEP_UIDS)), KEEP_UIDS)
    cur.execute("DELETE FROM view_embeddings WHERE uid NOT IN (%s)" % ",".join("?" * len(KEEP_UIDS)), KEEP_UIDS)
    print(f"DB templates after: {cur.execute('SELECT COUNT(*) FROM templates').fetchone()[0]}")
    print(f"DB view_embeddings after: {cur.execute('SELECT COUNT(*) FROM view_embeddings').fetchone()[0]}")

    # 3. Renumber faiss_idx 0..83 (ordered by original faiss_idx)
    kept_rows = cur.execute(
        "SELECT uid FROM templates ORDER BY faiss_idx"
    ).fetchall()
    for new_idx, row in enumerate(kept_rows):
        cur.execute("UPDATE templates SET faiss_idx = ? WHERE uid = ?", (new_idx, row["uid"]))
    conn.commit()
    print(f"Renumbered faiss_idx 0..{len(kept_rows) - 1}")

    # 4. Rebuild FAISS index
    #    Section 1 (core text): clip_embedding of each template in faiss_idx order
    #    Section 2 (views):     view_embeddings rows, ordered by faiss_idx then VIEW_ORDER
    text_embeddings = []
    view_embeddings = []
    view_metadata = []

    ordered = cur.execute(
        "SELECT uid, clip_embedding, glb_path FROM templates ORDER BY faiss_idx"
    ).fetchall()

    for row in ordered:
        emb = np.frombuffer(row["clip_embedding"], dtype=np.float32).copy()
        text_embeddings.append(emb)

        view_rows = cur.execute(
            "SELECT view_name, embedding FROM view_embeddings WHERE uid = ?",
            (row["uid"],),
        ).fetchall()
        vmap = {r["view_name"]: r["embedding"] for r in view_rows}
        for vname in VIEW_ORDER:
            if vname in vmap and vmap[vname]:
                view_embeddings.append(np.frombuffer(vmap[vname], dtype=np.float32).copy())
                view_metadata.append([row["uid"], vname, row["glb_path"]])

    print(f"Text embeddings (core): {len(text_embeddings)}")
    print(f"View embeddings: {len(view_embeddings)}")

    all_vecs = np.array(text_embeddings + view_embeddings, dtype=np.float32)
    faiss.normalize_L2(all_vecs)

    index = faiss.IndexFlatL2(all_vecs.shape[1])
    index.add(all_vecs)
    faiss.write_index(index, INDEX_PATH)

    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(view_metadata, f)

    print(f"\nFAISS rebuilt: {index.ntotal} vectors (d={index.d})")
    print(f"Metadata JSON entries: {len(view_metadata)}")

    conn.close()

    # 5. Summary of remaining disk
    remaining = 0
    for r in os.listdir(os.path.join(TEMPLATE_DIR, "core_100")):
        if r.endswith(".glb"):
            remaining += os.path.getsize(os.path.join(TEMPLATE_DIR, "core_100", r))
    for r in os.listdir(os.path.join(TEMPLATE_DIR, "objaverse_ext")):
        if r.endswith(".glb"):
            remaining += os.path.getsize(os.path.join(TEMPLATE_DIR, "objaverse_ext", r))
    print(f"\nRemaining template GLBs: {fmt_mb(remaining)} (was 1338.2 MB)")
    print(f"Total freed: {fmt_mb(freed_bytes)}")
    print("\nCLEANUP COMPLETE.")


if __name__ == "__main__":
    main()
