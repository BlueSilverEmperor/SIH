"""
Blender 3D Blueprint Generation Script (bpy)
Executed headlessly via Blender CLI: blender --background --python scripts/blender_3d_builder.py -- <output_path> <wall_count> <column_count> <slab_area>
"""

import sys
import os

try:
    import bpy
    import mathutils
    IS_BLENDER = True
except ImportError:
    IS_BLENDER = False

def create_blender_3d_blueprint(output_filepath, wall_count=16, column_count=20, slab_area=500.0):
    if not IS_BLENDER:
        print("[ERROR] bpy module not available in standard Python. Must run inside Blender executable context.")
        return False

    # Clear existing objects
    bpy.ops.wm.read_factory_settings(use_empty=True)
    
    # 1. Create Scene & Materials
    def get_or_create_material(name, color_rgba):
        mat = bpy.data.materials.get(name)
        if not mat:
            mat = bpy.data.materials.new(name=name)
            mat.use_nodes = True
            nodes = mat.node_tree.nodes
            principled = nodes.get("Principled BSDF")
            if principled:
                principled.inputs['Base Color'].default_value = color_rgba
        return mat

    concrete_mat = get_or_create_material("Concrete_Slab", (0.5, 0.52, 0.55, 1.0))
    wall_mat = get_or_create_material("Exterior_Wall", (0.2, 0.35, 0.5, 1.0))
    inner_wall_mat = get_or_create_material("Interior_Wall", (0.8, 0.82, 0.85, 1.0))
    steel_mat = get_or_create_material("Structural_Steel", (0.8, 0.45, 0.1, 1.0))

    # 2. Build Ground Foundation Slab
    slab_dim = (slab_area ** 0.5)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, -0.25))
    slab = bpy.context.active_object
    slab.name = "Foundation_Slab"
    slab.scale = (slab_dim, slab_dim, 0.5)
    slab.data.materials.append(concrete_mat)

    # 3. Build Perimeter Walls
    wall_height = 3.5
    half_slab = slab_dim / 2.0

    # Exterior Boundary Walls
    wall_positions = [
        ((0, half_slab, wall_height/2), (slab_dim, 0.3, wall_height)),
        ((0, -half_slab, wall_height/2), (slab_dim, 0.3, wall_height)),
        ((half_slab, 0, wall_height/2), (0.3, slab_dim, wall_height)),
        ((-half_slab, 0, wall_height/2), (0.3, slab_dim, wall_height)),
    ]

    for idx, (loc, scale) in enumerate(wall_positions):
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
        wall = bpy.context.active_object
        wall.name = f"Ext_Wall_{idx+1}"
        wall.scale = scale
        wall.data.materials.append(wall_mat)

    # 4. Build Interior Partition Walls
    grid_step = slab_dim / 4.0
    for i in range(1, int(wall_count) - 3):
        x_pos = -half_slab + (i % 4 + 1) * grid_step
        y_pos = -half_slab + ((i // 4) + 1) * grid_step
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(x_pos, y_pos, wall_height/2))
        iwall = bpy.context.active_object
        iwall.name = f"Int_Wall_{i}"
        iwall.scale = (grid_step * 0.8, 0.2, wall_height)
        iwall.data.materials.append(inner_wall_mat)

    # 5. Build Structural Steel Columns
    col_spacing = slab_dim / 5.0
    col_idx = 0
    for cx in range(5):
        for cy in range(5):
            if col_idx >= column_count:
                break
            px = -half_slab + (cx + 0.5) * col_spacing
            py = -half_slab + (cy + 0.5) * col_spacing
            bpy.ops.mesh.primitive_cylinder_add(radius=0.25, depth=wall_height + 0.5, location=(px, py, (wall_height+0.5)/2))
            col = bpy.context.active_object
            col.name = f"Steel_Column_{col_idx+1}"
            col.data.materials.append(steel_mat)
            col_idx += 1

    # 6. Setup Lighting & Camera
    bpy.ops.object.light_add(type='SUN', location=(10, 10, 20))
    sun = bpy.context.active_object
    sun.data.energy = 5.0

    # 7. Export Model (.glb or .obj)
    os.makedirs(os.path.dirname(output_filepath), exist_ok=True)

    if output_filepath.endswith('.glb') or output_filepath.endswith('.gltf'):
        bpy.ops.export_scene.gltf(filepath=output_filepath, export_format='GLB')
    else:
        # Export OBJ
        if hasattr(bpy.ops.wm, 'obj_export'):
            bpy.ops.wm.obj_export(filepath=output_filepath)
        else:
            bpy.ops.export_scene.obj(filepath=output_filepath)

    print(f"[SUCCESS] 3D Blueprint model generated via Blender -> {output_filepath}")
    return True

if __name__ == "__main__":
    args = sys.argv
    if "--" in args:
        cli_args = args[args.index("--") + 1:]
        out_path = cli_args[0] if len(cli_args) > 0 else "output.obj"
        w_cnt = int(cli_args[1]) if len(cli_args) > 1 else 16
        c_cnt = int(cli_args[2]) if len(cli_args) > 2 else 20
        area = float(cli_args[3]) if len(cli_args) > 3 else 500.0
        create_blender_3d_blueprint(out_path, w_cnt, c_cnt, area)
