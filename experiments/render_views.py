import os
import sys
import trimesh
import numpy as np

def render_views(mesh_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    scene = trimesh.load(mesh_path)
    mesh = scene if isinstance(scene, trimesh.Trimesh) else scene.dump(concatenate=True)

    centroid = mesh.centroid
    mesh.apply_translation(-centroid)
    scale = 1.0 / mesh.bounding_box.extents.max()
    mesh.apply_scale(scale)

    dist = 1.5
    angles = {"front": 0, "left": 90, "back": 180, "right": 270}

    for name, angle_deg in angles.items():
        angle_rad = np.radians(angle_deg)
        eye = np.array([np.sin(angle_rad) * dist, 0.0, np.cos(angle_rad) * dist])

        # Manually build camera transform: look_at(eye, center=origin, up=+Y)
        forward = np.array([0.0, 0.0, 0.0]) - eye
        forward = forward / np.linalg.norm(forward)
        up = np.array([0.0, 1.0, 0.0])
        right = np.cross(forward, up)
        right = right / np.linalg.norm(right)
        up = np.cross(right, forward)

        transform = np.eye(4)
        transform[:3, 0] = right
        transform[:3, 1] = up
        transform[:3, 2] = -forward  # camera looks down -Z
        transform[:3, 3] = eye

        sc = trimesh.Scene(mesh)
        sc.camera.resolution = (512, 512)
        sc.camera.fov = (30, 30)
        sc.camera_transform = transform

        png = sc.save_image(resolution=(512, 512), visible=True)
        out_path = os.path.join(output_dir, f"{name}.png")
        with open(out_path, "wb") as f:
            f.write(png)
        print(f"Rendered {name} -> {out_path}")

if __name__ == "__main__":
    mesh_path = sys.argv[1]
    output_dir = sys.argv[2]
    render_views(mesh_path, output_dir)
