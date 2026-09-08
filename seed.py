import os
import sys
import datetime
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'constructsync_project.settings')
django.setup()

from django.utils import timezone
from core.models import Project, WBSTask, FieldInput, ExtractedMetric, AnalyticsLog, Supplier, Blueprint3D
from services.evm_engine import calculate_project_evm
from services.supplier_engine import calculate_supplier_scores_and_softmax

def seed_database():
    """
    Populates database with realistic demo construction project data, WBS tasks, multi-modal field inputs, and EVM logs.
    """
    # Clear existing data
    Blueprint3D.objects.all().delete()
    ExtractedMetric.objects.all().delete()
    FieldInput.objects.all().delete()
    AnalyticsLog.objects.all().delete()
    WBSTask.objects.all().delete()
    Supplier.objects.all().delete()
    Project.objects.all().delete()

    # 1. Create Project
    project = Project.objects.create(
        name="Apex Commercial Tower Phase 2",
        code="PRJ-APEX-SIH26122",
        description="ConstructFlow AI Baseline: Construction of 28-story commercial office tower ($14.2M baseline, 250T Rebar Grade 60, Foundation Pour complete).",
        total_budget=14200000.0,
        start_date=datetime.date(2026, 1, 15),
        target_end_date=datetime.date(2026, 12, 30),
        geofence_latitude=37.7749,
        geofence_longitude=-122.4194,
        geofence_radius_meters=200.0,
        status="active"
    )

    # 2. Create WBS Tasks with Critical Path & Supplier Assignments
    wbs_data = [
        {"wbs_code": "1.1", "task_name": "Foundation Substructure Concrete Pouring", "planned_qty": 1200.0, "actual_qty": 1200.0, "unit": "cu.m", "unit_cost": 150.0, "actual_cost": 180000.0, "critical": True, "milestone": "Foundation Pour Complete", "p_start": datetime.date(2026, 1, 15), "p_end": datetime.date(2026, 3, 1)},
        {"wbs_code": "1.2", "task_name": "Structural Steel Rebar Fitting (250T Grade 60)", "planned_qty": 250.0, "actual_qty": 180.0, "unit": "tons", "unit_cost": 850.0, "actual_cost": 153000.0, "critical": True, "milestone": "Rebar Grade 60 Installation", "p_start": datetime.date(2026, 3, 2), "p_end": datetime.date(2026, 6, 15)},
        {"wbs_code": "1.3", "task_name": "Superstructure Column & Shear Wall Erection", "planned_qty": 850.0, "actual_qty": 420.0, "unit": "tons", "unit_cost": 1200.0, "actual_cost": 504000.0, "critical": True, "milestone": "Superstructure Core", "p_start": datetime.date(2026, 6, 16), "p_end": datetime.date(2026, 9, 30)},
        {"wbs_code": "2.1", "task_name": "Curtain Wall Glass Facade Glazing", "planned_qty": 3500.0, "actual_qty": 1100.0, "unit": "sq.m", "unit_cost": 220.0, "actual_cost": 242000.0, "critical": False, "milestone": "Envelope Closure", "p_start": datetime.date(2026, 7, 1), "p_end": datetime.date(2026, 11, 15)},
        {"wbs_code": "3.1", "task_name": "HVAC & MEP Riser Shaft Installation", "planned_qty": 800.0, "actual_qty": 220.0, "unit": "m", "unit_cost": 180.0, "actual_cost": 39600.0, "critical": False, "milestone": "MEP Core Energization", "p_start": datetime.date(2026, 8, 1), "p_end": datetime.date(2026, 12, 15)},
    ]

    tasks = []
    for w in wbs_data:
        task = WBSTask.objects.create(
            project=project,
            wbs_code=w["wbs_code"],
            task_name=w["task_name"],
            planned_quantity=w["planned_qty"],
            actual_quantity=w["actual_qty"],
            unit=w["unit"],
            unit_cost=w["unit_cost"],
            actual_cost=w["actual_cost"],
            start_date=w["p_start"],
            end_date=w["p_end"],
            planned_start_date=w["p_start"],
            planned_end_date=w["p_end"],
            is_critical_path=w["critical"],
            milestone_name=w["milestone"]
        )
        task.calculate_evm()
        task.save()
        tasks.append(task)

    # 3. Create Sample Field Inputs & AI Extractions
    sample_inputs = [
        {
            "type": "photo",
            "file": "uploads/photos/foundation_pour_01.jpg",
            "orig_name": "foundation_pour_01.jpg",
            "notes": "Foundation Pour verification for Apex Commercial Tower Phase 2.",
            "author": "Chief Inspector Marcus Vance",
            "status": "approved",
            "extracted": {
                "wbs_idx": 0,
                "qty": 1200.0,
                "unit": "cu.m",
                "material": "Substructure Ready-Mix Concrete (C40)",
                "labor": 18,
                "cost": 180000.0,
                "conf": 0.99,
                "reasoning": "CV scan confirmed 100% completion of Foundation Pour with 1200 cu.m slab placed."
            }
        },
        {
            "type": "invoice_pdf",
            "file": "uploads/invoices/inv_steel_rebar_884.pdf",
            "orig_name": "inv_steel_rebar_884.pdf",
            "notes": "Delivery invoice for 180T Rebar Grade 60 at Apex Tower Phase 2 site.",
            "author": "Procurement Dept",
            "status": "approved",
            "extracted": {
                "wbs_idx": 1,
                "qty": 180.0,
                "unit": "tons",
                "material": "Grade 60 Structural Steel Rebar",
                "labor": 12,
                "cost": 153000.0,
                "conf": 0.98,
                "reasoning": "Invoice parsing verified 180 tons of Grade 60 Rebar delivered at $850/ton."
            }
        }
    ]

    for item in sample_inputs:
        f_input = FieldInput.objects.create(
            project=project,
            input_type=item["type"],
            file_path=item["file"],
            original_filename=item["orig_name"],
            notes=item["notes"],
            source_author=item["author"],
            status=item["status"]
        )

        ext = item["extracted"]
        target_task = tasks[ext["wbs_idx"]] if ext["wbs_idx"] < len(tasks) else tasks[0]
        
        ExtractedMetric.objects.create(
            field_input=f_input,
            wbs_task=target_task,
            extracted_quantity=ext["qty"],
            unit=ext["unit"],
            detected_material=ext["material"],
            labor_count=ext["labor"],
            incurred_cost=ext["cost"],
            confidence_score=ext["conf"],
            ai_reasoning=ext["reasoning"],
            status=ext.get("status", "approved")
        )

    # 4. Create Suppliers Matrix Data
    suppliers_data = [
        {"name": "Tata Steel Infra", "category": "Steel Rebar", "email": "supply@tatasteel.com", "tco": 92.0, "delivery": 95.0, "quality": 96.0, "stability": 94.0, "esg": 88.0, "status": "preferred"},
        {"name": "Jindal Global Steel", "category": "Steel Rebar", "email": "b2b@jindalsteel.com", "tco": 86.0, "delivery": 88.0, "quality": 90.0, "stability": 91.0, "esg": 82.0, "status": "active"},
        {"name": "Apex Steel Industries", "category": "Steel Rebar", "email": "sales@apexsteel.com", "tco": 75.0, "delivery": 80.0, "quality": 82.0, "stability": 78.0, "esg": 70.0, "status": "under_review"},
        
        {"name": "Ultratech ReadyMix", "category": "Concrete", "email": "orders@ultratech.com", "tco": 94.0, "delivery": 96.0, "quality": 98.0, "stability": 95.0, "esg": 90.0, "status": "preferred"},
        {"name": "LafargeHolcim Concrete", "category": "Concrete", "email": "commercial@lafarge.com", "tco": 88.0, "delivery": 90.0, "quality": 92.0, "stability": 93.0, "esg": 94.0, "status": "active"},
        
        {"name": "Titanium Dynamics Corp", "category": "Titanium Billets", "email": "defense@ti-dynamics.com", "tco": 98.0, "delivery": 99.0, "quality": 99.5, "stability": 98.0, "esg": 95.0, "status": "preferred"}
    ]

    for s_data in suppliers_data:
        supplier = Supplier.objects.create(
            name=s_data["name"],
            category=s_data["category"],
            contact_email=s_data["email"],
            tco_score=s_data["tco"],
            delivery_score=s_data["delivery"],
            quality_score=s_data["quality"],
            stability_score=s_data["stability"],
            esg_score=s_data["esg"],
            status=s_data["status"]
        )
        supplier.calculate_weighted_score()
        supplier.save()

    # Calculate Softmax probabilities across categories
    calculate_supplier_scores_and_softmax()

    # 5. Create Initial 3D Blueprint Entry
    models_dir = os.path.join(os.path.dirname(__file__), 'static', 'models', '3d_blueprints')
    os.makedirs(models_dir, exist_ok=True)
    sample_model_path = "static/models/3d_blueprints/skyline_floor1_structure.obj"

    Blueprint3D.objects.create(
        project=project,
        name="Apex Commercial Tower Phase 2 - Structural Model",
        source_filename="foundation_pour_01.jpg",
        wall_count=24,
        column_count=32,
        slab_area_sqm=1200.0,
        model_file_path=sample_model_path,
        format="obj",
        status="generated"
    )

    # 6. Seed Attendance, Weather Hedging, and Procurement Records
    from core.models import AttendanceRecord, WeatherRiskLog, ProcurementReviewItem
    AttendanceRecord.objects.all().delete()
    
    # Active Worker 1 (Verified On-Site)
    AttendanceRecord.objects.create(
        project=project,
        worker_id="WRK-1001",
        worker_name="Alex Rivera",
        worker_role="Site Inspector",
        trade_category="Quality Assurance",
        hourly_rate=55.0,
        shift_type="morning_checkin",
        checkin_time=timezone.now() - datetime.timedelta(hours=4),
        latitude=37.77495,
        longitude=-122.41942,
        distance_from_center_m=8.5,
        checkin_lat=37.77495,
        checkin_lng=-122.41942,
        checkin_distance_m=8.5,
        is_geofence_valid=True,
        token_hash="a1b2c3d4e5f67890",
        status="verified",
        shift_status="ACTIVE_ON_SITE",
        associated_wbs_task=tasks[0] if len(tasks) > 0 else None
    )

    # Active Worker 2 (Verified On-Site)
    AttendanceRecord.objects.create(
        project=project,
        worker_id="WRK-1002",
        worker_name="Maria Santos",
        worker_role="Concrete Superintendent",
        trade_category="Concrete Works",
        hourly_rate=50.0,
        shift_type="morning_checkin",
        checkin_time=timezone.now() - datetime.timedelta(hours=3, minutes=30),
        latitude=37.77501,
        longitude=-122.41938,
        distance_from_center_m=12.1,
        checkin_lat=37.77501,
        checkin_lng=-122.41938,
        checkin_distance_m=12.1,
        is_geofence_valid=True,
        status="verified",
        shift_status="ACTIVE_ON_SITE",
        associated_wbs_task=tasks[1] if len(tasks) > 1 else None
    )

    # Completed Shift Worker 3
    rec3 = AttendanceRecord.objects.create(
        project=project,
        worker_id="WRK-1003",
        worker_name="David Chen",
        worker_role="Steel Rebar Foreman",
        trade_category="Structural Steel",
        hourly_rate=48.0,
        shift_type="evening_checkout",
        checkin_time=timezone.now() - datetime.timedelta(hours=9),
        checkout_time=timezone.now() - datetime.timedelta(hours=1),
        latitude=37.77490,
        longitude=-122.41940,
        distance_from_center_m=4.2,
        checkin_lat=37.77490,
        checkin_lng=-122.41940,
        checkin_distance_m=4.2,
        checkout_lat=37.77492,
        checkout_lng=-122.41941,
        checkout_distance_m=5.1,
        is_geofence_valid=True,
        status="verified",
        shift_status="COMPLETED",
        associated_wbs_task=tasks[1] if len(tasks) > 1 else None
    )
    rec3.calculate_shift_totals()
    rec3.save()

    WeatherRiskLog.objects.create(
        project=project,
        log_date=datetime.date.today(),
        forecast_condition="Heavy Rain & High Winds",
        precipitation_chance_pct=85.0,
        wind_speed_kmh=42.0,
        temperature_c=18.5,
        impacted_tasks_count=3,
        risk_severity="severe",
        buffer_days_added=3,
        details_json='[{"wbs_code": "1.2", "task_name": "Rebar Grade 60 Erection", "vulnerability": "High Wind Risk"}]'
    )

    tata_supplier = Supplier.objects.filter(name="Tata Steel Infra").first()
    ti_supplier = Supplier.objects.filter(name="Titanium Dynamics Corp").first()
    
    ProcurementReviewItem.objects.create(
        project=project,
        material_name="Grade 60 High-Yield Steel Rebar",
        category="Steel Rebar",
        quantity=250.0,
        unit="tons",
        estimated_unit_cost=850.0,
        total_estimated_cost=212500.0,
        recommended_supplier=tata_supplier,
        softmax_score=0.785,
        status="approved"
    )

    # 7. Seed Real-Time CCTV Cameras
    from core.models import CCTVCamera, CCTVStreamLog
    CCTVStreamLog.objects.all().delete()
    CCTVCamera.objects.all().delete()

    cctv_cams = [
        {
            "name": "Apex Zone A Foundation Concrete Cam",
            "code": "CAM-ZONE-A",
            "loc": "Foundation Sector 1",
            "rtsp": "rtsp://admin:pass@192.168.1.101:554/live1",
            "type": "mjpg",
            "task": tasks[0] if len(tasks) > 0 else None
        },
        {
            "name": "Apex Zone B Rebar Grade 60 Assembly Cam",
            "code": "CAM-ZONE-B",
            "loc": "Rebar Deck Level 2",
            "rtsp": "rtsp://admin:pass@192.168.1.102:554/live1",
            "type": "mjpg",
            "task": tasks[1] if len(tasks) > 1 else None
        },
        {
            "name": "DockFlow Berth 3 Vessels Telemetry Cam",
            "code": "CAM-BERTH-3",
            "loc": "Drydock Berth 3",
            "rtsp": "rtsp://admin:pass@192.168.1.103:554/live1",
            "type": "mjpg",
            "task": None
        },
        {
            "name": "TurnaroundOS CDU Reactor Purge Telemetry Cam",
            "code": "CAM-CDU-REACTOR",
            "loc": "CDU Catalyst Tower",
            "rtsp": "rtsp://admin:pass@192.168.1.104:554/live1",
            "type": "mjpg",
            "task": None
        }
    ]

    for c in cctv_cams:
        CCTVCamera.objects.create(
            project=project,
            name=c["name"],
            camera_code=c["code"],
            location_tag=c["loc"],
            rtsp_url=c["rtsp"],
            stream_type=c["type"],
            resolution="1080p",
            fps=30,
            status="online",
            associated_wbs_task=c["task"]
        )

    # 8. Seed Multi-Industry Sub-App Domain Records (SIH26122 Required Datasets)
    from core.models import BoMComponent, DrydockBerth, ITARVendorAudit, TurnaroundShutdown
    BoMComponent.objects.all().delete()
    DrydockBerth.objects.all().delete()
    ITARVendorAudit.objects.all().delete()
    TurnaroundShutdown.objects.all().delete()

    # PlantFlow AI: Automated EV Drive Unit Assembly Line A (500 units/day target, SKU-ST-882 Stator Cores, Stator Winding active)
    BoMComponent.objects.create(
        project=project,
        part_number="SKU-ST-882",
        component_name="Automated EV Drive Unit Assembly Line A - Stator Cores",
        workstation="Automated EV Assembly Line A",
        active_phase="Stator Winding Active",
        daily_target_units=500.0,
        daily_actual_units=485.0,
        bom_quantity=500.0,
        target_line_rate_units_hr=50.0,
        actual_line_rate_units_hr=48.5,
        status="optimal"
    )
    BoMComponent.objects.create(
        project=project,
        part_number="SKU-RO-901",
        component_name="Automated EV Drive Unit Assembly Line A - Rotor Shafts",
        workstation="Automated EV Assembly Line A",
        active_phase="Rotor Balancing & Precision Fit",
        daily_target_units=500.0,
        daily_actual_units=490.0,
        bom_quantity=500.0,
        target_line_rate_units_hr=50.0,
        actual_line_rate_units_hr=49.0,
        status="optimal"
    )

    # DockFlow AI: Offshore Patrol Vessel Hull #409 (Berth 3, 800T DH36 Steel Plates, Main Deck Welding 74%)
    cam_berth3 = CCTVCamera.objects.filter(camera_code="CAM-BERTH-3").first()
    DrydockBerth.objects.create(
        project=project,
        berth_code="BERTH-03",
        vessel_name="Offshore Patrol Vessel",
        hull_number="Hull #409",
        hull_section="Main Deck Section H-04",
        steel_tonnage=800.0,
        steel_grade="DH36 Steel Plates",
        main_deck_welding_pct=74.0,
        docking_status="docked",
        completion_percentage=74.0,
        telemetry_camera=cam_berth3
    )

    # AeroGuard AI: Avionic Telemetry Housing Machining - Batch VII (ITAR Level 3, Titanium Ti-6Al-4V Billets, Metallurgical Audit passed)
    ITARVendorAudit.objects.create(
        project=project,
        supplier=ti_supplier if ti_supplier else tata_supplier,
        batch_code="Batch VII",
        component_housing="Avionic Telemetry Housing Machining",
        itar_registration_number="ITAR-DEF-90082-US",
        itar_level="ITAR Level 3",
        material_billet_type="Titanium Ti-6Al-4V Billets",
        clearance_level="Top Secret (TS/SCI)",
        metallurgical_audit_status="Passed",
        audit_status="compliant",
        compliance_score=99.8
    )

    # TurnaroundOS AI: Crude Distillation Unit (CDU) Catalyst Regeneration (96-hour window, Type-V Catalyst Pellets, Reactor Purge complete)
    TurnaroundShutdown.objects.create(
        project=project,
        unit_name="Crude Distillation Unit (CDU)",
        catalyst_regeneration_task="CDU Catalyst Regeneration",
        turnaround_window_hours=96,
        catalyst_pellet_type="Type-V Catalyst Pellets",
        purge_status="Reactor Purge Complete",
        shutdown_phase="overhaul",
        hot_work_permits_count=8,
        flare_stack_status="normal",
        hazard_level="low",
        completion_percentage=78.5
    )

    # 9. Trigger initial EVM calculation snapshot
    calculate_project_evm(project.id)
    print("Database successfully seeded with demo project data, suppliers, 3D blueprints, CCTV cameras, and multi-industry enterprise sub-apps!")


if __name__ == "__main__":
    seed_database()


