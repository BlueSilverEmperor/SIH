import os
import sys
import subprocess
import shutil
import math
import time
from core.models import Blueprint3D, Project
from services.addon_manager import is_addon_enabled

def find_blender_executable():
    """
    Attempts to locate the Blender executable on system PATH or default Windows installation directories.
    """
    blender_path = shutil.which("blender")
    if blender_path:
        return blender_path

    possible_paths = [
        r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 3.5\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender\blender.exe"
    ]
    for p in possible_paths:
        if os.path.exists(p):
            return p

    return None

def generate_procedural_3d_obj_fallback(output_obj_path, wall_count=16, column_count=20, slab_area=500.0, building_type='residential_house', stories=2, unique_seed=12345):
    """
    Ultra-Detailed Architectural 3D CAD (.obj + .mtl) Exporter.
    Generates exact architectural components:
    - Glazed Multi-Pane Windows with Anodized Trim Frames & Grids
    - Main Entrance & Egress Doors with Frames & Handles
    - Rooftop HVAC Chillers, Air Intake Vents, Exhaust Pipes & Ducting
    - Porch Steps & Guard Railings
    - Structural Steel Columns & Brick Chimneys
    """
    os.makedirs(os.path.dirname(output_obj_path), exist_ok=True)
    mtl_filename = os.path.splitext(os.path.basename(output_obj_path))[0] + ".mtl"
    mtl_filepath = os.path.join(os.path.dirname(output_obj_path), mtl_filename)

    with open(mtl_filepath, "w") as f_mtl:
        f_mtl.write("""# ConstructSync AI Ultra-Detailed Architectural 3D Materials
newmtl Concrete_Slab
Kd 0.35 0.38 0.42
Ka 0.20 0.20 0.20
Ks 0.10 0.10 0.10
Ns 10

newmtl Exterior_Wall
Kd 0.90 0.90 0.86
Ka 0.30 0.30 0.28
Ks 0.20 0.20 0.20
Ns 20

newmtl Interior_Wall
Kd 0.96 0.96 0.96
Ka 0.40 0.40 0.40
Ks 0.10 0.10 0.10
Ns 10

newmtl Window_Glass
Kd 0.20 0.65 0.95
Ka 0.15 0.35 0.55
Ks 0.95 0.95 0.95
Ns 100
d 0.45

newmtl Window_Frame
Kd 0.10 0.12 0.15
Ka 0.10 0.10 0.10
Ks 0.50 0.50 0.50
Ns 40

newmtl Door_Wood
Kd 0.55 0.30 0.15
Ka 0.20 0.10 0.05
Ks 0.30 0.30 0.30
Ns 30

newmtl Door_Frame
Kd 0.20 0.22 0.25
Ka 0.15 0.15 0.15
Ks 0.40 0.40 0.40
Ns 30

newmtl Roof_Vents
Kd 0.65 0.68 0.72
Ka 0.25 0.25 0.25
Ks 0.85 0.85 0.85
Ns 70

newmtl Railing_Metal
Kd 0.30 0.35 0.40
Ka 0.15 0.15 0.15
Ks 0.60 0.60 0.60
Ns 50

newmtl Structural_Steel
Kd 0.85 0.45 0.10
Ka 0.30 0.15 0.05
Ks 0.70 0.70 0.70
Ns 60

newmtl Roof_Shingles
Kd 0.18 0.20 0.25
Ka 0.10 0.10 0.12
Ks 0.20 0.20 0.20
Ns 15

newmtl Brick_Chimney
Kd 0.70 0.25 0.15
Ka 0.25 0.10 0.05
Ks 0.15 0.15 0.15
Ns 15

newmtl Porch_Deck
Kd 0.65 0.50 0.35
Ka 0.20 0.15 0.10
Ks 0.20 0.20 0.20
Ns 20
""")

    vertices = []
    objects = []

    def add_box(name, mat_name, center_x, center_y, center_z, size_x, size_y, size_z):
        nonlocal vertices, objects
        start_v_idx = len(vertices) + 1
        hx, hy, hz = size_x / 2.0, size_y / 2.0, size_z / 2.0

        box_verts = [
            (center_x - hx, center_y - hy, center_z - hz),
            (center_x + hx, center_y - hy, center_z - hz),
            (center_x + hx, center_y + hy, center_z - hz),
            (center_x - hx, center_y + hy, center_z - hz),
            (center_x - hx, center_y - hy, center_z + hz),
            (center_x + hx, center_y - hy, center_z + hz),
            (center_x + hx, center_y + hy, center_z + hz),
            (center_x - hx, center_y + hy, center_z + hz),
        ]
        vertices.extend(box_verts)

        v = start_v_idx
        box_faces = [
            (v+4, v+5, v+6, v+7),
            (v+0, v+3, v+2, v+1),
            (v+3, v+7, v+6, v+2),
            (v+0, v+1, v+5, v+4),
            (v+1, v+2, v+6, v+5),
            (v+0, v+4, v+7, v+3),
        ]
        objects.append({
            'name': name,
            'material': mat_name,
            'faces': box_faces
        })

    def add_roof_pitch(name, mat_name, center_x, base_y, center_z, width_x, height_y, depth_z):
        nonlocal vertices, objects
        start_v_idx = len(vertices) + 1
        hx, hz = width_x / 2.0, depth_z / 2.0

        roof_verts = [
            (center_x - hx, base_y, center_z - hz),
            (center_x + hx, base_y, center_z - hz),
            (center_x + hx, base_y, center_z + hz),
            (center_x - hx, base_y, center_z + hz),
            (center_x, base_y + height_y, center_z - hz),
            (center_x, base_y + height_y, center_z + hz),
        ]
        vertices.extend(roof_verts)

        v = start_v_idx
        roof_faces = [
            (v+0, v+3, v+2, v+1),
            (v+0, v+1, v+4, v+4),
            (v+2, v+3, v+5, v+5),
            (v+1, v+2, v+5, v+4),
            (v+0, v+4, v+5, v+3),
        ]
        objects.append({
            'name': name,
            'material': mat_name,
            'faces': roof_faces
        })

    # --- HELPER: DETAILED FRAMED WINDOW WITH GLASS & MULLION GRIDS ---
    def add_framed_window(prefix, cx, cy, cz, width, height, is_side_wall=False):
        t_frame = 0.08
        if not is_side_wall:
            # Window Frame Border (Front / Back Wall)
            add_box(f"{prefix}_Frame_Top", "Window_Frame", cx, cy + height/2.0 - t_frame/2.0, cz, width, t_frame, 0.32)
            add_box(f"{prefix}_Frame_Btm", "Window_Frame", cx, cy - height/2.0 + t_frame/2.0, cz, width, t_frame, 0.32)
            add_box(f"{prefix}_Frame_L", "Window_Frame", cx - width/2.0 + t_frame/2.0, cy, cz, t_frame, height, 0.32)
            add_box(f"{prefix}_Frame_R", "Window_Frame", cx + width/2.0 - t_frame/2.0, cy, cz, t_frame, height, 0.32)
            # Center Mullion Divider Grid
            add_box(f"{prefix}_Mullion_V", "Window_Frame", cx, cy, cz, t_frame*0.8, height - t_frame*2, 0.30)
            add_box(f"{prefix}_Mullion_H", "Window_Frame", cx, cy, cz, width - t_frame*2, t_frame*0.8, 0.30)
            # Glass Pane
            add_box(f"{prefix}_Glass", "Window_Glass", cx, cy, cz, width - t_frame*2, height - t_frame*2, 0.10)
        else:
            # Window Frame Border (East / West Wall)
            add_box(f"{prefix}_Frame_Top", "Window_Frame", cx, cy + height/2.0 - t_frame/2.0, cz, 0.32, t_frame, width)
            add_box(f"{prefix}_Frame_Btm", "Window_Frame", cx, cy - height/2.0 + t_frame/2.0, cz, 0.32, t_frame, width)
            add_box(f"{prefix}_Frame_L", "Window_Frame", cx, cy, cz - width/2.0 + t_frame/2.0, 0.32, height, t_frame)
            add_box(f"{prefix}_Frame_R", "Window_Frame", cx, cy, cz + width/2.0 - t_frame/2.0, 0.32, height, t_frame)
            # Center Mullion Divider Grid
            add_box(f"{prefix}_Mullion_V", "Window_Frame", cx, cy, cz, 0.30, height - t_frame*2, t_frame*0.8)
            add_box(f"{prefix}_Mullion_H", "Window_Frame", cx, cy, cz, 0.30, t_frame*0.8, width - t_frame*2)
            # Glass Pane
            add_box(f"{prefix}_Glass", "Window_Glass", cx, cy, cz, 0.10, height - t_frame*2, width - t_frame*2)

    # --- HELPER: DETAILED DOOR WITH FRAME & HANDLE ---
    def add_framed_door(prefix, cx, cy, cz, width, height, is_side_wall=False):
        t_frame = 0.1
        if not is_side_wall:
            add_box(f"{prefix}_Frame_Top", "Door_Frame", cx, cy + height/2.0 - t_frame/2.0, cz, width, t_frame, 0.32)
            add_box(f"{prefix}_Frame_L", "Door_Frame", cx - width/2.0 + t_frame/2.0, cy, cz, t_frame, height, 0.32)
            add_box(f"{prefix}_Frame_R", "Door_Frame", cx + width/2.0 - t_frame/2.0, cy, cz, t_frame, height, 0.32)
            # Door Wood Panel
            add_box(f"{prefix}_Panel", "Door_Wood", cx, cy - t_frame/2.0, cz, width - t_frame*2, height - t_frame, 0.12)
            # Metallic Handle / Knob
            add_box(f"{prefix}_Handle", "Structural_Steel", cx + width*0.35, cy, cz + 0.10, 0.08, 0.18, 0.12)
        else:
            add_box(f"{prefix}_Frame_Top", "Door_Frame", cx, cy + height/2.0 - t_frame/2.0, cz, 0.32, t_frame, width)
            add_box(f"{prefix}_Frame_L", "Door_Frame", cx, cy, cz - width/2.0 + t_frame/2.0, 0.32, height, t_frame)
            add_box(f"{prefix}_Frame_R", "Door_Frame", cx, cy, cz + width/2.0 - t_frame/2.0, 0.32, height, t_frame)
            add_box(f"{prefix}_Panel", "Door_Wood", cx, cy - t_frame/2.0, cz, 0.12, height - t_frame, width - t_frame*2)
            add_box(f"{prefix}_Handle", "Structural_Steel", cx + 0.10, cy, cz + width*0.35, 0.12, 0.18, 0.08)

    # --- HELPER: ROOFTOP HVAC VENTILATION CHILLER & DUCTWORK ---
    def add_hvac_ventilation(prefix, cx, cy, cz, size_x, size_z):
        # HVAC Main Unit Box
        add_box(f"{prefix}_HVAC_Unit", "Roof_Vents", cx, cy + 0.6, cz, size_x, 1.2, size_z)
        # Louvered Intake Grille
        add_box(f"{prefix}_Intake_Grille", "Roof_Vents", cx, cy + 0.6, cz + size_z/2.0 + 0.02, size_x * 0.8, 0.8, 0.05)
        # Exhaust Stack Flue Pipe
        add_box(f"{prefix}_Exhaust_Pipe_1", "Roof_Vents", cx - size_x*0.25, cy + 1.5, cz, 0.4, 0.8, 0.4)
        add_box(f"{prefix}_Exhaust_Pipe_2", "Roof_Vents", cx + size_x*0.25, cy + 1.5, cz, 0.4, 0.8, 0.4)
        # Horizontal Air Ducting
        add_box(f"{prefix}_Air_Duct", "Roof_Vents", cx, cy + 0.3, cz - size_z*0.75, 0.5, 0.4, size_z * 0.6)

    # --- HELPER: PORCH ENTRANCE STEPS & GUARD RAILINGS ---
    def add_entrance_steps_and_railings(prefix, cx, cy, cz, width, depth):
        # 3 Entrance Steps
        step_h = 0.15
        for s in range(3):
            sw = width - s * 0.15
            sd = depth / 3.0
            add_box(f"{prefix}_Step_{s+1}", "Concrete_Slab", cx, cy - (s * step_h), cz + s * sd, sw, step_h, sd)

        # Metal Guard Railings along porch
        r_height = 1.0
        add_box(f"{prefix}_Railing_Top_L", "Railing_Metal", cx - width/2.0 + 0.05, cy + r_height, cz, 0.05, 0.05, depth)
        add_box(f"{prefix}_Railing_Top_R", "Railing_Metal", cx + width/2.0 - 0.05, cy + r_height, cz, 0.05, 0.05, depth)

        for p in range(4):
            pz = cz - depth/2.0 + p * (depth/3.0)
            add_box(f"{prefix}_Railing_Post_L_{p}", "Railing_Metal", cx - width/2.0 + 0.05, cy + r_height/2.0, pz, 0.04, r_height, 0.04)
            add_box(f"{prefix}_Railing_Post_R_{p}", "Railing_Metal", cx + width/2.0 - 0.05, cy + r_height/2.0, pz, 0.04, r_height, 0.04)

    # Spatial Footprint Dimensions
    aspect_r = 1.2 + ((unique_seed % 7) / 10.0)
    w_dim = round(math.sqrt(slab_area * aspect_r), 1)
    d_dim = round(math.sqrt(slab_area / aspect_r), 1)
    half_w, half_d = w_dim / 2.0, d_dim / 2.0
    wall_h = 3.2

    # =========================================================================
    # --- ARCHETYPE A: COMMERCIAL SKYSCRAPER / OFFICE TOWER ---
    # =========================================================================
    if building_type == 'commercial_tower':
        num_floors = max(4, min(12, stories))
        add_box("Foundation_Slab", "Concrete_Slab", 0, -0.25, 0, w_dim + 2.0, 0.5, d_dim + 2.0)
        add_box("Elevator_Core", "Concrete_Slab", 0, (num_floors * wall_h)/2.0, 0, w_dim * 0.3, num_floors * wall_h, d_dim * 0.3)

        # Entrance Doors at Ground Floor
        add_framed_door("Main_Entrance_L", -2.5, 1.2, half_d, 2.0, 2.4)
        add_framed_door("Main_Entrance_R", 2.5, 1.2, half_d, 2.0, 2.4)

        for fl in range(num_floors):
            fy = fl * wall_h + wall_h / 2.0
            add_box(f"Floor_Slab_{fl+1}", "Concrete_Slab", 0, fl * wall_h, 0, w_dim + 0.4, 0.25, d_dim + 0.4)
            
            # Framed Glass Windows across facade
            for wx in range(-2, 3):
                if fl > 0 or abs(wx) > 1:
                    add_framed_window(f"Tower_Win_F{fl+1}_N_{wx}", wx * (w_dim/5.5), fy, -half_d, w_dim/6.5, wall_h - 0.4)
                    add_framed_window(f"Tower_Win_F{fl+1}_S_{wx}", wx * (w_dim/5.5), fy, half_d, w_dim/6.5, wall_h - 0.4)

            # Corner Steel Columns
            add_box(f"Steel_Col_{fl+1}_1", "Structural_Steel", -half_w, fy, -half_d, 0.4, wall_h, 0.4)
            add_box(f"Steel_Col_{fl+1}_2", "Structural_Steel", half_w, fy, -half_d, 0.4, wall_h, 0.4)
            add_box(f"Steel_Col_{fl+1}_3", "Structural_Steel", half_w, fy, half_d, 0.4, wall_h, 0.4)
            add_box(f"Steel_Col_{fl+1}_4", "Structural_Steel", -half_w, fy, half_d, 0.4, wall_h, 0.4)

        # Rooftop Helipad & Multi-Unit HVAC Chillers / Air Vents
        roof_y = num_floors * wall_h
        add_box("Roof_Slab", "Roof_Shingles", 0, roof_y, 0, w_dim + 0.6, 0.3, d_dim + 0.6)
        add_hvac_ventilation("Roof_HVAC_1", -w_dim*0.25, roof_y, -d_dim*0.25, w_dim*0.3, d_dim*0.3)
        add_hvac_ventilation("Roof_HVAC_2", w_dim*0.25, roof_y, -d_dim*0.25, w_dim*0.3, d_dim*0.3)

    # =========================================================================
    # --- ARCHETYPE B: INDUSTRIAL WAREHOUSE / LOGISTICS ---
    # =========================================================================
    elif building_type == 'warehouse':
        wh_h = 5.5
        add_box("Foundation_Slab", "Concrete_Slab", 0, -0.25, 0, w_dim + 1.0, 0.5, d_dim + 1.0)
        
        # Outer Walls
        add_box("Ext_Wall_North", "Exterior_Wall", 0, wh_h/2.0, -half_d, w_dim, wh_h, 0.3)
        add_box("Ext_Wall_South", "Exterior_Wall", 0, wh_h/2.0, half_d, w_dim, wh_h, 0.3)
        add_box("Ext_Wall_East", "Exterior_Wall", half_w, wh_h/2.0, 0, 0.3, wh_h, d_dim)
        add_box("Ext_Wall_West", "Exterior_Wall", -half_w, wh_h/2.0, 0, 0.3, wh_h, d_dim)

        # Framed Industrial Loading Dock Doors
        for d_idx in range(3):
            dx = -half_w * 0.5 + d_idx * (half_w * 0.5)
            add_framed_door(f"Loading_Dock_{d_idx+1}", dx, 2.0, half_d, 3.5, 4.0)

        # High Steel Columns
        for cx in range(4):
            for cz in range(3):
                px = -half_w + (cx + 0.5) * (w_dim / 4.0)
                pz = -half_d + (cz + 0.5) * (d_dim / 3.0)
                add_box(f"Steel_Truss_{cx}_{cz}", "Structural_Steel", px, wh_h/2.0, pz, 0.5, wh_h, 0.5)

        # Industrial Roof & Multiple Air Exhaust Vents
        add_box("Industrial_Roof", "Roof_Shingles", 0, wh_h + 0.2, 0, w_dim + 0.5, 0.3, d_dim + 0.5)
        for v in range(4):
            vx = -half_w * 0.6 + v * (w_dim * 0.4)
            add_hvac_ventilation(f"Warehouse_Vent_{v+1}", vx, wh_h + 0.3, 0, 2.5, 2.5)

    # =========================================================================
    # --- ARCHETYPE C: HOSPITALS / INSTITUTIONAL COMPLEX ---
    # =========================================================================
    elif building_type == 'hospital':
        h_floors = max(3, stories)
        add_box("Foundation_Slab_Main", "Concrete_Slab", 0, -0.25, 0, w_dim, 0.5, d_dim)
        add_box("Foundation_Slab_Wing", "Concrete_Slab", w_dim*0.6, -0.25, 0, w_dim*0.5, 0.5, d_dim*0.8)

        add_framed_door("Hospital_Emergency_Entrance", 0, 1.2, half_d, 3.0, 2.4)

        for fl in range(h_floors):
            fy = fl * wall_h + wall_h / 2.0
            add_box(f"Main_Block_Fl{fl+1}", "Exterior_Wall", 0, fy, 0, w_dim, wall_h - 0.1, d_dim)
            add_box(f"Wing_Block_Fl{fl+1}", "Exterior_Wall", w_dim*0.6, fy, 0, w_dim*0.5, wall_h - 0.1, d_dim*0.8)
            # Framed Windows
            for wx in range(-2, 3):
                add_framed_window(f"Hosp_Win_N_{fl+1}_{wx}", wx * (w_dim/5.5), fy, -half_d, w_dim/6.5, 1.6)

        # Rooftop Helipad & Medical HVAC Chillers
        roof_y = h_floors * wall_h
        add_box("Helipad_Slab", "Concrete_Slab", 0, roof_y + 0.2, 0, w_dim * 0.5, 0.4, d_dim * 0.5)
        add_hvac_ventilation("Hospital_Chiller_1", -w_dim*0.3, roof_y, -d_dim*0.2, 3.0, 3.0)

    # =========================================================================
    # --- ARCHETYPE D / DEFAULT: RESIDENTIAL HOUSE / FARMHOUSE ---
    # =========================================================================
    else:
        # 1. Foundation Concrete Slab
        add_box("Foundation_Slab", "Concrete_Slab", 0, -0.25, 0, w_dim + 1.2, 0.5, d_dim + 1.2)

        # 2. Porch Deck, Entrance Steps & Guard Railings
        porch_w = w_dim * 0.45
        porch_d = 2.8
        add_box("Porch_Deck", "Porch_Deck", 0, -0.1, half_d + porch_d/2.0, porch_w, 0.3, porch_d)
        add_entrance_steps_and_railings("Porch_Entrance", 0, -0.1, half_d + porch_d, 2.2, 1.2)

        # 3. 1st Floor Exterior Walls
        door_w, door_h = 2.0, 2.4
        seg_w = (w_dim - door_w) / 2.0
        add_box("Ext_Wall_North", "Exterior_Wall", 0, wall_h/2.0, -half_d, w_dim, wall_h, 0.3)
        add_box("Ext_Wall_South_L", "Exterior_Wall", -half_w + seg_w/2.0, wall_h/2.0, half_d, seg_w, wall_h, 0.3)
        add_box("Ext_Wall_South_R", "Exterior_Wall", half_w - seg_w/2.0, wall_h/2.0, half_d, seg_w, wall_h, 0.3)
        add_box("Ext_Wall_South_Lintel", "Exterior_Wall", 0, door_h + (wall_h - door_h)/2.0, half_d, door_w, wall_h - door_h, 0.3)

        # Main Entrance Door with Framed Border & Handle
        add_framed_door("Main_Front_Door", 0, door_h/2.0, half_d, door_w, door_h)

        add_box("Ext_Wall_East", "Exterior_Wall", half_w, wall_h/2.0, 0, 0.3, wall_h, d_dim)
        add_box("Ext_Wall_West", "Exterior_Wall", -half_w, wall_h/2.0, 0, 0.3, wall_h, d_dim)

        # 1st Floor Framed Glazed Windows (Front, Back, East, West)
        win_w, win_h, win_y = 1.8, 1.4, 1.8
        add_framed_window("Window_East_1", half_w, win_y, -half_d*0.4, win_w, win_h, is_side_wall=True)
        add_framed_window("Window_East_2", half_w, win_y, half_d*0.4, win_w, win_h, is_side_wall=True)
        add_framed_window("Window_West_1", -half_w, win_y, -half_d*0.4, win_w, win_h, is_side_wall=True)
        add_framed_window("Window_West_2", -half_w, win_y, half_d*0.4, win_w, win_h, is_side_wall=True)

        # 1st Floor Interior Room Partitions
        add_box("Int_Wall_1", "Interior_Wall", -w_dim*0.1, wall_h/2.0, 0, 0.2, wall_h, d_dim*0.8)
        add_box("Int_Wall_2", "Interior_Wall", half_w*0.5, wall_h/2.0, half_d*0.3, w_dim*0.45, wall_h, 0.2)

        # Brick Masonry Chimney Stack with Exhaust Flue Vent
        add_box("Masonry_Chimney", "Brick_Chimney", -w_dim*0.2, wall_h * 1.2, -half_d*0.2, 1.4, wall_h * 3.0, 1.4)
        add_box("Chimney_Flue_Pipe", "Roof_Vents", -w_dim*0.2, wall_h * 2.7, -half_d*0.2, 0.5, 0.8, 0.5)

        if stories >= 2:
            # 2nd Floor Joists & Floor Slab
            add_box("Second_Floor_Slab", "Concrete_Slab", 0, wall_h, 0, w_dim + 0.3, 0.25, d_dim + 0.3)
            wall_y2 = wall_h + wall_h / 2.0
            
            add_box("Ext_Wall_North_2F", "Exterior_Wall", 0, wall_y2, -half_d, w_dim, wall_h, 0.3)
            add_box("Ext_Wall_South_2F", "Exterior_Wall", 0, wall_y2, half_d, w_dim, wall_h, 0.3)
            add_box("Ext_Wall_East_2F", "Exterior_Wall", half_w, wall_y2, 0, 0.3, wall_h, d_dim)
            add_box("Ext_Wall_West_2F", "Exterior_Wall", -half_w, wall_y2, 0, 0.3, wall_h, d_dim)

            # 2nd Floor Framed Windows
            add_framed_window("Window_2F_South_1", -half_w*0.5, wall_y2, half_d, win_w, win_h)
            add_framed_window("Window_2F_South_2", half_w*0.5, wall_y2, half_d, win_w, win_h)
            add_framed_window("Window_2F_North_1", -half_w*0.5, wall_y2, -half_d, win_w, win_h)

            # Roof Pitch & Rooftop Exhaust Vent Pipes
            roof_base_y = wall_h * 2.0
            add_box("Roof_Cap_Base", "Roof_Shingles", 0, roof_base_y + 0.1, 0, w_dim + 0.8, 0.25, d_dim + 0.8)
            add_roof_pitch("Roof_Gable_Pitch", "Roof_Shingles", 0, roof_base_y + 0.25, 0, w_dim + 1.0, 4.5, d_dim + 1.0)

            # Roof Ridge Exhaust Vent
            add_hvac_ventilation("Roof_Ridge_Vent", w_dim*0.2, roof_base_y + 3.8, 0, 1.8, 1.2)
        else:
            add_roof_pitch("Roof_Gable_Pitch", "Roof_Shingles", 0, wall_h + 0.25, 0, w_dim + 1.0, 4.0, d_dim + 1.0)
            add_hvac_ventilation("Roof_Vent", w_dim*0.2, wall_h + 3.0, 0, 1.8, 1.2)

    # Write .obj file
    with open(output_obj_path, "w") as f_obj:
        f_obj.write(f"mtllib {mtl_filename}\n")
        f_obj.write(f"# ConstructSync AI Ultra-Detailed 3D Model - {building_type.title()}\n\n")

        for vx, vy, vz in vertices:
            f_obj.write(f"v {vx:.4f} {vy:.4f} {vz:.4f}\n")

        f_obj.write("\n")

        for obj in objects:
            f_obj.write(f"g {obj['name']}\n")
            f_obj.write(f"usemtl {obj['material']}\n")
            for f in obj['faces']:
                f_obj.write(f"f {f[0]} {f[1]} {f[2]} {f[3]}\n")
            f_obj.write("\n")

    print(f"[SUCCESS] Ultra-Detailed Architectural 3D Model generated ({building_type}) -> {output_obj_path}")
    return True

def generate_3d_blueprint(project_id, blueprint_name="Generated 3D Model", source_filename=None, wall_count=16, column_count=20, slab_area=500.0, building_type='residential_house', stories=2, unique_seed=12345, content_hash=None, ai_reasoning=None):
    """
    Main entry point for generating 3D Blueprint models with 100% deterministic asset paths per file upload.
    Same blueprint file content = Exact same 3D model asset.
    Different blueprint file content = Completely different 3D model asset.
    """
    project = Project.objects.filter(id=project_id).first()
    if not project:
        raise ValueError(f"Project with ID {project_id} not found.")

    if not is_addon_enabled(project_id, 'blender_3d_generator'):
        raise PermissionError("Blender 3D Blueprint Generator Add-On is disabled for this project.")

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    output_dir = os.path.join(base_dir, 'static', 'models', '3d_blueprints')
    os.makedirs(output_dir, exist_ok=True)

    hash_key = content_hash or f"{source_filename}_{slab_area}_{wall_count}_{column_count}_{unique_seed}"
    short_hash = hash_key[:12]
    filename = f"bp_proj{project_id}_{short_hash}.obj"
    rel_file_path = f"static/models/3d_blueprints/{filename}"
    full_output_path = os.path.join(output_dir, filename)



    blender_exe = find_blender_executable()
    script_path = os.path.join(base_dir, 'scripts', 'blender_3d_builder.py')
    generation_method = "blender_bpy"

    if blender_exe and os.path.exists(script_path):
        cmd = [
            blender_exe,
            "--background",
            "--python", script_path,
            "--",
            full_output_path,
            str(wall_count),
            str(column_count),
            str(slab_area)
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if res.returncode != 0:
                generate_procedural_3d_obj_fallback(full_output_path, wall_count, column_count, slab_area, building_type, stories, unique_seed)
                generation_method = "procedural_fallback"
        except Exception:
            generate_procedural_3d_obj_fallback(full_output_path, wall_count, column_count, slab_area, building_type, stories, unique_seed)
            generation_method = "procedural_fallback"
    else:
        generate_procedural_3d_obj_fallback(full_output_path, wall_count, column_count, slab_area, building_type, stories, unique_seed)
        generation_method = "procedural_fallback"

    project = Project.objects.filter(id=project_id).first()
    blueprint = Blueprint3D.objects.create(
        project=project,
        name=blueprint_name,
        source_filename=source_filename or "2D_Technical_Blueprint.pdf",
        wall_count=wall_count,
        column_count=column_count,
        slab_area_sqm=slab_area,
        model_file_path=rel_file_path,
        format="obj",
        status="generated"
    )

    # Save generated 3D model into NoSQL project table
    try:
        from services.nosql_storage import save_file_to_nosql
        save_file_to_nosql(
            project_id=project_id,
            relative_file_path=rel_file_path,
            file_category='3d_blueprint_model',
            original_filename=source_filename or f"{blueprint_name}.obj",
            notes=f"Generated 3D Model ({generation_method})",
            metadata={'wall_count': wall_count, 'column_count': column_count, 'slab_area_sqm': slab_area, 'format': 'obj'}
        )
    except Exception:
        pass

    result = blueprint.to_dict()
    result['generation_method'] = generation_method
    if ai_reasoning:
        result['ai_reasoning'] = ai_reasoning
    return result

