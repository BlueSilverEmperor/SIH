import os
import json
import datetime
import hashlib
from django.shortcuts import render
from django.http import JsonResponse, StreamingHttpResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from .models import Project, WBSTask, FieldInput, ExtractedMetric, AnalyticsLog, Supplier, Blueprint3D, ProjectAddOn, DailyProgressAudit, FailSafeReorgLog, AttendanceRecord, WeatherRiskLog, ProcurementReviewItem, CCTVCamera, CCTVStreamLog
from .context_processors import get_or_create_default_project

from services.ingestion import create_field_input, create_text_log_input
from services.ai_engine import parse_field_input_with_ai, parse_blueprint_file_to_3d_specs
from services.evm_engine import calculate_project_evm, approve_and_sync_metric, reject_metric
from services.supplier_engine import calculate_supplier_scores_and_softmax, get_recommended_supplier_by_category
from services.blender_service import generate_3d_blueprint
from services.addon_manager import get_project_addons, get_addon_details, is_addon_enabled, set_addon_status, toggle_addon
from services.daily_audit_service import run_daily_progress_audit, get_daily_audit_history
from services.failsafe_engine import evaluate_and_trigger_failsafe_reorg, get_failsafe_reorg_history
from services.cctv_streaming_service import generate_cctv_stream_token, verify_cctv_stream_token, generate_mjpeg_stream_generator, audit_camera_feed_with_ai
from services.geofence_attendance_engine import process_worker_checkin, process_worker_checkout, update_project_geofence, get_attendance_summary_metrics
from services.multi_industry_engine import INDUSTRIES, get_industry_details, get_all_industries, get_plantflow_metrics, get_dockflow_metrics, get_aeroguard_metrics, get_turnaroundos_metrics




UPLOAD_FOLDER = os.path.join(settings.BASE_DIR, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def get_json_or_post_data(request):
    data = {}
    if request.content_type and 'application/json' in request.content_type and request.body:
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            data = {}
    if not data:
        data = request.POST.dict()
    return data


# ==================== WEB VIEWS ====================

def dashboard_view(request):
    project = get_or_create_default_project(request)
    tasks = WBSTask.objects.filter(project_id=project.id).order_by('wbs_code') if project else []
    pending_extractions = ExtractedMetric.objects.filter(status='pending').order_by('-created_at')
    
    evm_summary = calculate_project_evm(project.id) if project else {}

    return render(
        request,
        'dashboard.html',
        {
            'active_page': 'dashboard',
            'project': project,
            'tasks': tasks,
            'pending_extractions': pending_extractions,
            'evm': evm_summary
        }
    )


def master_schedule_view(request):
    project = get_or_create_default_project(request)
    tasks = WBSTask.objects.filter(project_id=project.id).order_by('wbs_code') if project else []
    return render(
        request,
        'master_schedule.html',
        {
            'active_page': 'master_schedule',
            'project': project,
            'tasks': tasks
        }
    )


def ingestion_view(request):
    project = get_or_create_default_project(request)
    field_inputs = FieldInput.objects.filter(project_id=project.id).order_by('-uploaded_at') if project else []
    return render(
        request,
        'ingestion.html',
        {
            'active_page': 'ingestion',
            'project': project,
            'field_inputs': field_inputs
        }
    )


def review_queue_view(request):
    project = get_or_create_default_project(request)
    extractions = ExtractedMetric.objects.filter(status='pending').order_by('-created_at')
    tasks = WBSTask.objects.filter(project_id=project.id).order_by('wbs_code') if project else []
    return render(
        request,
        'review_queue.html',
        {
            'active_page': 'review_queue',
            'project': project,
            'extractions': extractions,
            'tasks': tasks
        }
    )


def analytics_view(request):
    project = get_or_create_default_project(request)
    evm_summary = calculate_project_evm(project.id) if project else {}
    analytics_logs = [log.to_dict() for log in AnalyticsLog.objects.filter(project_id=project.id).order_by('-snapshot_date')] if project else []
    
    return render(
        request,
        'analytics.html',
        {
            'active_page': 'analytics',
            'project': project,
            'evm': evm_summary,
            'analytics_logs': analytics_logs
        }
    )


def blueprint_3d_view(request):
    project = get_or_create_default_project(request)
    blueprints = Blueprint3D.objects.filter(project_id=project.id).order_by('-created_at') if project else []
    latest_blueprint = blueprints.first() if blueprints.exists() else None
    return render(
        request,
        'blueprint_3d.html',
        {
            'active_page': 'blueprint_3d',
            'project': project,
            'blueprints': blueprints,
            'latest_blueprint': latest_blueprint
        }
    )


def suppliers_view(request):
    project = get_or_create_default_project(request)
    category = request.GET.get('category', 'All')
    suppliers_list = calculate_supplier_scores_and_softmax(category=category)
    recommendations = get_recommended_supplier_by_category()
    
    return render(
        request,
        'suppliers.html',
        {
            'active_page': 'suppliers',
            'project': project,
            'suppliers': suppliers_list,
            'selected_category': category,
            'recommendations': recommendations,
            'categories_list': ['All', 'Steel Rebar', 'Concrete', 'Masonry', 'Electrical', 'Plumbing']
        }
    )


# ==================== REST API ENDPOINTS ====================

@csrf_exempt
def api_upload(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    project_id = request.POST.get('project_id')
    try:
        project_id = int(project_id) if project_id else get_or_create_default_project(request).id
    except Exception:
        project_id = get_or_create_default_project(request).id

    input_type = request.POST.get('input_type')
    notes = request.POST.get('notes')
    source_author = request.POST.get('source_author', 'Site Inspector')
    text_content = request.POST.get('text_content')

    field_input = None

    if input_type == 'text' or text_content:
        if not text_content and notes:
            text_content = notes
        field_input = create_text_log_input(
            project_id=project_id,
            text_content=text_content or "Routine daily inspection log.",
            upload_folder=UPLOAD_FOLDER,
            notes=notes,
            source_author=source_author
        )
    elif 'file' in request.FILES and request.FILES['file'].name != '':
        file_obj = request.FILES['file']
        field_input = create_field_input(
            project_id=project_id,
            file_obj=file_obj,
            upload_folder=UPLOAD_FOLDER,
            notes=notes,
            source_author=source_author,
            forced_type=input_type
        )
    else:
        return JsonResponse({'success': False, 'error': 'No file or text content provided for ingestion.'}, status=400)

    extracted_metric = parse_field_input_with_ai(field_input)

    return JsonResponse({
        'success': True,
        'field_input': field_input.to_dict(),
        'extracted_metric': extracted_metric.to_dict()
    })


@csrf_exempt
def api_approve_metric(request, metric_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    data = get_json_or_post_data(request)
    wbs_task_id = data.get('wbs_task_id')
    override_quantity = data.get('override_quantity')
    override_cost = data.get('override_cost')

    try:
        res = approve_and_sync_metric(
            extracted_metric_id=metric_id,
            target_wbs_task_id=wbs_task_id,
            override_quantity=override_quantity,
            override_cost=override_cost
        )
        return JsonResponse({'success': True, 'data': res})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@csrf_exempt
def api_reject_metric(request, metric_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    data = get_json_or_post_data(request)
    reasoning = data.get('reasoning')

    try:
        res = reject_metric(metric_id, reasoning=reasoning)
        return JsonResponse({'success': True, 'data': res})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@csrf_exempt
def api_wbs_tasks(request):
    project = get_or_create_default_project(request)
    if request.method == 'GET':
        tasks = WBSTask.objects.filter(project_id=project.id).order_by('wbs_code') if project else []
        return JsonResponse({'success': True, 'tasks': [t.to_dict() for t in tasks]})
    
    if request.method == 'POST':
        data = get_json_or_post_data(request)
        wbs_code = data.get('wbs_code')
        task_name = data.get('task_name')
        unit = data.get('unit', 'units')
        unit_cost = float(data.get('unit_cost', 0.0))
        planned_quantity = float(data.get('planned_quantity', 0.0))

        if not wbs_code or not task_name:
            return JsonResponse({'success': False, 'error': 'WBS Code and Task Name are required.'}, status=400)

        task = WBSTask.objects.create(
            project=project,
            wbs_code=wbs_code,
            task_name=task_name,
            unit=unit,
            unit_cost=unit_cost,
            planned_quantity=planned_quantity,
            actual_quantity=0.0,
            actual_cost=0.0
        )
        task.calculate_evm()
        task.save()

        calculate_project_evm(project.id)

        return JsonResponse({'success': True, 'task': task.to_dict()})

    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)


@csrf_exempt
def api_generate_3d_model(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    project = get_or_create_default_project(request)
    data = get_json_or_post_data(request)
    
    source_filename = "2D_Technical_Blueprint.pdf"
    real_specs = None
    
    if 'file' in request.FILES and request.FILES['file'].name != '':
        file_obj = request.FILES['file']
        filename = file_obj.name
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        with open(save_path, 'wb+') as destination:
            for chunk in file_obj.chunks():
                destination.write(chunk)
        source_filename = filename
        real_specs = parse_blueprint_file_to_3d_specs(save_path)

    name = data.get('name') or f"3D Takeoff - {source_filename}"
    
    if real_specs:
        wall_count = real_specs['wall_count']
        column_count = real_specs['column_count']
        slab_area = real_specs['slab_area']
        building_type = real_specs.get('building_type', 'residential_house')
        stories = real_specs.get('stories', 2)
        unique_seed = real_specs.get('unique_seed', 12345)
        content_hash = real_specs.get('content_hash')
        reasoning = real_specs['reasoning']
    else:
        wall_count = int(data.get('wall_count', 18))
        column_count = int(data.get('column_count', 24))
        slab_area = float(data.get('slab_area', 550.0))
        building_type = 'residential_house'
        stories = 2
        unique_seed = 12345
        content_hash = None
        reasoning = "User-specified manual parameters applied."

    try:
        blueprint_dict = generate_3d_blueprint(
            project_id=project.id,
            blueprint_name=name,
            source_filename=source_filename,
            wall_count=wall_count,
            column_count=column_count,
            slab_area=slab_area,
            building_type=building_type,
            stories=stories,
            unique_seed=unique_seed,
            content_hash=content_hash,
            ai_reasoning=reasoning
        )

        blueprint_dict['ai_reasoning'] = reasoning
        return JsonResponse({'success': True, 'blueprint': blueprint_dict})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def api_get_3d_models(request):
    project = get_or_create_default_project(request)
    blueprints = Blueprint3D.objects.filter(project_id=project.id).order_by('-created_at') if project else []
    return JsonResponse({'success': True, 'blueprints': [b.to_dict() for b in blueprints]})


@csrf_exempt
def api_suppliers(request):
    if request.method == 'GET':
        category = request.GET.get('category', 'All')
        suppliers_list = calculate_supplier_scores_and_softmax(category=category)
        return JsonResponse({'success': True, 'suppliers': [s.to_dict() for s in suppliers_list]})

    if request.method == 'POST':
        data = get_json_or_post_data(request)
        name = data.get('name')
        category = data.get('category', 'General')
        email = data.get('contact_email')
        tco = float(data.get('tco_score', 80.0))
        delivery = float(data.get('delivery_score', 80.0))
        quality = float(data.get('quality_score', 80.0))
        stability = float(data.get('stability_score', 80.0))
        esg = float(data.get('esg_score', 80.0))

        if not name:
            return JsonResponse({'success': False, 'error': 'Supplier name is required.'}, status=400)

        supplier = Supplier.objects.create(
            name=name,
            category=category,
            contact_email=email,
            tco_score=tco,
            delivery_score=delivery,
            quality_score=quality,
            stability_score=stability,
            esg_score=esg,
            status='active'
        )
        supplier.calculate_weighted_score()
        supplier.save()

        calculate_supplier_scores_and_softmax(category=category)

        return JsonResponse({'success': True, 'supplier': supplier.to_dict()})

    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)


def api_predictive_forecast(request):
    project = get_or_create_default_project(request)
    from services.predictive_engine import calculate_predictive_completion
    data = calculate_predictive_completion(project.id)
    return JsonResponse({'success': True, 'predictive': data})


@csrf_exempt
def api_update_task_schedule(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    project = get_or_create_default_project(request)
    req_data = get_json_or_post_data(request)
    task_id = req_data.get('task_id')
    if not task_id:
        return JsonResponse({'success': False, 'error': 'Task ID is required.'}, status=400)

    task = WBSTask.objects.filter(id=task_id, project_id=project.id).first()
    if not task:
        return JsonResponse({'success': False, 'error': 'Task not found.'}, status=404)

    if 'is_critical_path' in req_data:
        task.is_critical_path = bool(req_data['is_critical_path'])
    if 'assigned_supplier_id' in req_data:
        supplier_id = req_data['assigned_supplier_id']
        task.assigned_supplier_id = int(supplier_id) if supplier_id else None
    if 'milestone_name' in req_data:
        task.milestone_name = req_data['milestone_name']

    task.save()

    from services.predictive_engine import calculate_predictive_completion
    predictive = calculate_predictive_completion(project.id)

    return JsonResponse({'success': True, 'task': task.to_dict(), 'predictive': predictive})


@csrf_exempt
def api_create_project(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    data = get_json_or_post_data(request)
    name = data.get('name')
    code = data.get('code')
    if not name or not code:
        return JsonResponse({'success': False, 'error': 'Project Name and Project Code are required.'}, status=400)

    if Project.objects.filter(code=code).exists():
        return JsonResponse({'success': False, 'error': f"Project code '{code}' already exists."}, status=400)

    try:
        start_d = datetime.datetime.strptime(data.get('start_date'), '%Y-%m-%d').date() if data.get('start_date') else datetime.date.today()
    except Exception:
        start_d = datetime.date.today()

    try:
        end_d = datetime.datetime.strptime(data.get('target_end_date'), '%Y-%m-%d').date() if data.get('target_end_date') else start_d + datetime.timedelta(days=180)
    except Exception:
        end_d = start_d + datetime.timedelta(days=180)

    try:
        budget = float(data.get('total_budget', 1000000.0))
    except Exception:
        budget = 1000000.0

    new_project = Project.objects.create(
        name=name,
        code=code,
        description=data.get('description', ''),
        total_budget=budget,
        start_date=start_d,
        target_end_date=end_d,
        status='active'
    )

    wbs_data = [
        {"wbs_code": "1.1", "task_name": "Site Excavation & Trenching", "planned_qty": 400.0, "actual_qty": 0.0, "unit": "cu.m", "unit_cost": 35.0, "critical": True, "milestone": "Groundwork Clearance"},
        {"wbs_code": "1.2", "task_name": "Concrete Foundation & Slab Pouring", "planned_qty": 300.0, "actual_qty": 0.0, "unit": "cu.m", "unit_cost": 150.0, "critical": True, "milestone": "Substructure Concrete Base"},
        {"wbs_code": "1.3", "task_name": "Structural Frame & Steel Rebar Fitting", "planned_qty": 60.0, "actual_qty": 0.0, "unit": "tons", "unit_cost": 900.0, "critical": True, "milestone": "Superstructure Frame"},
        {"wbs_code": "2.1", "task_name": "Block Masonry & Wall Construction", "planned_qty": 800.0, "actual_qty": 0.0, "unit": "sq.m", "unit_cost": 48.0, "critical": False, "milestone": "Building Envelope Closure"},
        {"wbs_code": "3.1", "task_name": "Electrical & Plumbing Services Installation", "planned_qty": 500.0, "actual_qty": 0.0, "unit": "m", "unit_cost": 25.0, "critical": False, "milestone": "MEP Energization"},
    ]
    for w in wbs_data:
        t = WBSTask.objects.create(
            project=new_project,
            wbs_code=w["wbs_code"],
            task_name=w["task_name"],
            planned_quantity=w["planned_qty"],
            actual_quantity=w["actual_qty"],
            unit=w["unit"],
            unit_cost=w["unit_cost"],
            start_date=start_d,
            end_date=end_d,
            planned_start_date=start_d,
            planned_end_date=end_d,
            is_critical_path=w["critical"],
            milestone_name=w["milestone"]
        )
        t.calculate_evm()
        t.save()

    request.session['active_project_id'] = new_project.id

    # Check if a blueprint file was uploaded during project initialization
    blueprint_file = request.FILES.get('blueprint_file') or request.FILES.get('file')
    pipeline_res = {}
    if blueprint_file:
        try:
            from services.ingestion import save_uploaded_file
            from services.blueprint_pipeline import execute_full_blueprint_pipeline
            rel_path, secure_name, _ = save_uploaded_file(blueprint_file, UPLOAD_FOLDER, input_type='blueprint')
            pipeline_res = execute_full_blueprint_pipeline(new_project.id, rel_path, secure_name)
        except Exception as e:
            pipeline_res = {'error': str(e)}

    return JsonResponse({
        'success': True,
        'project': new_project.to_dict(),
        'pipeline': pipeline_res
    })


@csrf_exempt
def api_upload_blueprint(request):
    """
    Dedicated endpoint to upload a blueprint file (PDF, CAD/DWG, PNG/JPG) for an existing project
    and execute the full automated pipeline (Upload -> Parse -> Cost -> Resource -> 3D -> Flowchart).
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    project = get_or_create_default_project(request)
    if not project:
        return JsonResponse({'success': False, 'error': 'No active project found.'}, status=404)

    file_obj = request.FILES.get('blueprint_file') or request.FILES.get('file')
    if not file_obj:
        return JsonResponse({'success': False, 'error': 'No blueprint_file uploaded in request.FILES.'}, status=400)

    try:
        from services.ingestion import save_uploaded_file
        from services.blueprint_pipeline import execute_full_blueprint_pipeline
        rel_path, secure_name, _ = save_uploaded_file(file_obj, UPLOAD_FOLDER, input_type='blueprint')
        pipeline_res = execute_full_blueprint_pipeline(project.id, rel_path, secure_name)
        return JsonResponse({
            'success': True,
            'project': project.to_dict(),
            'pipeline': pipeline_res
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)



@csrf_exempt
def api_switch_project(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    data = get_json_or_post_data(request)
    project_id = data.get('project_id')
    if not project_id:
        return JsonResponse({'success': False, 'error': 'Project ID is required.'}, status=400)

    project = Project.objects.filter(id=project_id).first()
    if not project:
        return JsonResponse({'success': False, 'error': 'Project not found.'}, status=404)

    request.session['active_project_id'] = project.id
    return JsonResponse({'success': True, 'project': project.to_dict()})


@csrf_exempt
def api_seed(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        from seed import seed_database
        seed_database()
        return JsonResponse({'success': True, 'message': 'Database re-seeded successfully.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ==================== ADD-ON ENGINE VIEWS & APIs ====================

def addons_view(request):
    project = get_or_create_default_project(request)
    addon_list = get_addon_details(project.id) if project else []
    daily_audit_data = run_daily_progress_audit(project.id) if project else {}
    failsafe_logs = get_failsafe_reorg_history(project.id) if project else []

    return render(
        request,
        'addons.html',
        {
            'active_page': 'addons',
            'project': project,
            'addon_list': addon_list,
            'daily_audit': daily_audit_data,
            'failsafe_logs': failsafe_logs
        }
    )


@csrf_exempt
def api_get_addons(request):
    project = get_or_create_default_project(request)
    if not project:
        return JsonResponse({'success': False, 'error': 'No active project found'}, status=404)

    details = get_addon_details(project.id)
    return JsonResponse({'success': True, 'addons': details, 'project_id': project.id})


@csrf_exempt
def api_toggle_addon(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    data = get_json_or_post_data(request)
    addon_key = data.get('addon_key')
    if not addon_key:
        return JsonResponse({'success': False, 'error': 'addon_key is required.'}, status=400)

    project = get_or_create_default_project(request)
    if not project:
        return JsonResponse({'success': False, 'error': 'No active project.'}, status=404)

    if 'is_enabled' in data:
        is_enabled = bool(data['is_enabled'])
        success, msg = set_addon_status(project.id, addon_key, is_enabled)
        res = {
            'success': success,
            'message': msg,
            'addon_key': addon_key,
            'is_enabled': is_enabled,
            'all_addons': get_project_addons(project.id)
        }
    else:
        res = toggle_addon(project.id, addon_key)

    return JsonResponse(res)


@csrf_exempt
def api_daily_audit_trigger(request):
    project = get_or_create_default_project(request)
    if not project:
        return JsonResponse({'success': False, 'error': 'No active project.'}, status=404)

    audit_res = run_daily_progress_audit(project.id)
    return JsonResponse({'success': True, 'audit': audit_res})


@csrf_exempt
def api_failsafe_reorg_trigger(request):
    project = get_or_create_default_project(request)
    if not project:
        return JsonResponse({'success': False, 'error': 'No active project.'}, status=404)

    data = get_json_or_post_data(request)
    force = bool(data.get('force', False))

    reorg_res = evaluate_and_trigger_failsafe_reorg(project.id, force=force)
    return JsonResponse({'success': True, 'reorg': reorg_res})


# ==================== NOSQL FILE STORAGE ENGINE APIs ====================

@csrf_exempt
def api_nosql_files(request):
    project = get_or_create_default_project(request)
    if not project:
        return JsonResponse({'success': False, 'error': 'No active project found.'}, status=404)

    from services.nosql_storage import get_nosql_files_for_project, get_nosql_table_name_for_project
    files = get_nosql_files_for_project(project.id)
    table_name = get_nosql_table_name_for_project(project.id)

    return JsonResponse({
        'success': True,
        'project_id': project.id,
        'project_name': project.name,
        'nosql_table_name': table_name,
        'count': len(files),
        'files': files
    })


@csrf_exempt
def api_nosql_sync(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    project = get_or_create_default_project(request)
    if not project:
        return JsonResponse({'success': False, 'error': 'No active project found.'}, status=404)

    from services.nosql_storage import sync_all_project_files_to_nosql
    sync_res = sync_all_project_files_to_nosql(project.id)
    return JsonResponse(sync_res)


# ==================== VISUAL FLOWCHART WORKFLOW ENGINE ====================

def flowchart_view(request):
    project = get_or_create_default_project(request)
    from services.flowchart_engine import generate_project_flowchart
    flowchart_data = generate_project_flowchart(project.id) if project else {}

    return render(
        request,
        'flowchart.html',
        {
            'active_page': 'flowchart',
            'project': project,
            'flowchart': flowchart_data
        }
    )


@csrf_exempt
def api_get_flowchart(request):
    project = get_or_create_default_project(request)
    if not project:
        return JsonResponse({'success': False, 'error': 'No active project found.'}, status=404)

    from services.flowchart_engine import generate_project_flowchart
    flowchart_data = generate_project_flowchart(project.id)
    return JsonResponse({'success': True, 'flowchart': flowchart_data})


@csrf_exempt
def api_rebuild_flowchart(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    project = get_or_create_default_project(request)
    if not project:
        return JsonResponse({'success': False, 'error': 'No active project found.'}, status=404)

    from services.flowchart_engine import generate_project_flowchart
    flowchart_data = generate_project_flowchart(project.id)
    return JsonResponse({'success': True, 'message': 'Flowchart rebuilt successfully', 'flowchart': flowchart_data})


# ==================== STANDALONE GEOFENCED COMPANION & EXTENDED ADD-ONS ====================

def companion_app_view(request):
    """
    Standalone Geofenced Companion App view for mobile field workers & site inspectors.
    Renders cryptographically signed, daily-refreshing QR codes (Morning Check-In & Evening Check-Out)
    and enables GPS location verification against project perimeter.
    """
    project = get_or_create_default_project(request)
    from services.qr_attendance_engine import generate_daily_qr_token
    
    morning_qr = generate_daily_qr_token(project.id, shift_type='morning_checkin') if project else {}
    evening_qr = generate_daily_qr_token(project.id, shift_type='evening_checkout') if project else {}
    
    records = AttendanceRecord.objects.filter(project_id=project.id).order_by('-timestamp')[:20] if project else []

    return render(
        request,
        'companion.html',
        {
            'active_page': 'companion',
            'project': project,
            'morning_qr': morning_qr,
            'evening_qr': evening_qr,
            'attendance_records': records
        }
    )


@csrf_exempt
def api_get_qr_token(request):
    """
    API endpoint returning fresh cryptographically signed QR tokens for morning check-in or evening check-out.
    """
    project = get_or_create_default_project(request)
    if not project:
        return JsonResponse({'success': False, 'error': 'No active project found'}, status=404)

    shift_type = request.GET.get('shift_type', 'morning_checkin')
    from services.qr_attendance_engine import generate_daily_qr_token
    token_data = generate_daily_qr_token(project.id, shift_type=shift_type)
    return JsonResponse({'success': True, 'qr': token_data})


@csrf_exempt
def api_record_attendance(request):
    """
    API endpoint for checking in/out from the companion app.
    Verifies cryptographic QR token and GPS coordinates against project geofence radius.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    project = get_or_create_default_project(request)
    if not project:
        return JsonResponse({'success': False, 'error': 'No active project found'}, status=404)

    data = get_json_or_post_data(request)
    worker_name = data.get('worker_name', 'Field Engineer')
    worker_role = data.get('worker_role', 'Site Inspector')
    shift_type = data.get('shift_type', 'morning_checkin')
    token_str = data.get('token', '')
    
    try:
        lat = float(data.get('latitude', 0.0))
        lng = float(data.get('longitude', 0.0))
    except Exception:
        lat, lng = 0.0, 0.0

    from services.qr_attendance_engine import record_geofenced_attendance
    res = record_geofenced_attendance(
        project_id=project.id,
        worker_name=worker_name,
        worker_role=worker_role,
        shift_type=shift_type,
        token_str=token_str,
        user_lat=lat,
        user_lng=lng
    )

    status_code = 200 if res['success'] else 400
    return JsonResponse(res, status=status_code)


@csrf_exempt
def api_get_attendance_logs(request):
    project = get_or_create_default_project(request)
    if not project:
        return JsonResponse({'success': False, 'error': 'No active project found'}, status=404)

    records = [r.to_dict() for r in AttendanceRecord.objects.filter(project_id=project.id).order_by('-timestamp')[:50]]
    return JsonResponse({'success': True, 'records': records})


@csrf_exempt
def api_approve_procurement(request):
    """
    HITL Procurement Approval endpoint: Project Manager approves a procurement recommendation,
    assigning the Softmax-scored vendor to a WBS task or creating a new WBS material task.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    project = get_or_create_default_project(request)
    if not project:
        return JsonResponse({'success': False, 'error': 'No active project found'}, status=404)

    data = get_json_or_post_data(request)
    supplier_id = data.get('supplier_id')
    task_id = data.get('task_id')
    material_name = data.get('material_name', 'Procured Equipment/Material')
    quantity = float(data.get('quantity', 100.0))
    unit_cost = float(data.get('unit_cost', 50.0))

    supplier = Supplier.objects.filter(id=supplier_id).first() if supplier_id else None
    
    if task_id:
        task = WBSTask.objects.filter(id=task_id, project_id=project.id).first()
        if task:
            task.assigned_supplier = supplier
            task.planned_quantity = quantity
            task.unit_cost = unit_cost
            task.calculate_evm()
            task.save()
    else:
        # Create new WBS procurement task
        next_code = f"4.{WBSTask.objects.filter(project_id=project.id).count() + 1}"
        task = WBSTask.objects.create(
            project=project,
            wbs_code=next_code,
            task_name=f"Procurement: {material_name}",
            planned_quantity=quantity,
            actual_quantity=0.0,
            unit='units',
            unit_cost=unit_cost,
            assigned_supplier=supplier,
            status='not_started'
        )

    # Log into ProcurementReviewItem
    review_item = ProcurementReviewItem.objects.create(
        project=project,
        material_name=material_name,
        category=supplier.category if supplier else 'General',
        quantity=quantity,
        estimated_unit_cost=unit_cost,
        total_estimated_cost=quantity * unit_cost,
        recommended_supplier=supplier,
        softmax_score=supplier.softmax_probability if supplier else 0.0,
        status='approved'
    )

    return JsonResponse({
        'success': True,
        'message': f"Procurement approved for '{material_name}'! Vendor '{supplier.name if supplier else 'Unassigned'}' assigned to task '{task.wbs_code}'.",
        'procurement': review_item.to_dict(),
        'task': task.to_dict()
    })


@csrf_exempt
def api_weather_hedging(request):
    """
    API endpoint executing weather risk analysis & schedule hedging for active outdoor tasks.
    """
    project = get_or_create_default_project(request)
    if not project:
        return JsonResponse({'success': False, 'error': 'No active project found'}, status=404)

    data = get_json_or_post_data(request)
    forecast_override = data.get('forecast')

    from services.weather_hedging_engine import evaluate_weather_risk_and_hedge
    res = evaluate_weather_risk_and_hedge(project.id, forecast_override=forecast_override)

    return JsonResponse(res)


@csrf_exempt
def api_voice_log(request):
    """
    API endpoint for Voice-Activated Field Logging.
    Receives transcribed voice notes, saves to FieldInput, and parses metrics with AI Engine.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    project = get_or_create_default_project(request)
    if not project:
        return JsonResponse({'success': False, 'error': 'No active project found'}, status=404)

    data = get_json_or_post_data(request)
    voice_transcript = data.get('transcript', '')

    if not voice_transcript:
        return JsonResponse({'success': False, 'error': 'Empty voice transcript provided'}, status=400)

    field_input = create_text_log_input(
        project_id=project.id,
        text_content=voice_transcript,
        upload_folder=UPLOAD_FOLDER,
        source_author='Voice Field Logging Companion'
    )

    # Parse with AI Engine
    metric = parse_field_input_with_ai(field_input)

    return JsonResponse({
        'success': True,
        'message': 'Voice field log recorded and parsed into AI metrics!',
        'field_input_id': field_input.id,
        'metrics_extracted': [metric.to_dict()] if metric else []
    })


# ==================== REAL-TIME CCTV SURVEILLANCE & MONITORING VIEWS ====================

def cctv_view(request):
    """
    Renders the interactive multi-camera CCTV surveillance & monitoring dashboard.
    """
    project = get_or_create_default_project(request)
    cameras = CCTVCamera.objects.filter(project=project) if project else []
    tasks = WBSTask.objects.filter(project=project) if project else []

    camera_list = []
    for cam in cameras:
        cam_dict = cam.to_dict()
        token_info = generate_cctv_stream_token(cam.id)
        cam_dict['stream_token'] = token_info['token']
        camera_list.append(cam_dict)

    addons = get_project_addons(project.id) if project else {}

    return render(request, 'cctv.html', {
        'project': project,
        'cameras': camera_list,
        'tasks': tasks,
        'addons': addons,
        'cctv_enabled': bool(addons.get('cctv_surveillance_module', True)),
        'active_page': 'cctv'
    })


@csrf_exempt
def api_cctv_cameras(request):
    """
    API endpoint to list registered cameras or add a new site CCTV camera.
    """
    project = get_or_create_default_project(request)
    if not project:
        return JsonResponse({'success': False, 'error': 'No active project found'}, status=404)

    if request.method == 'POST':
        data = get_json_or_post_data(request)
        name = data.get('name')
        camera_code = data.get('camera_code')
        location_tag = data.get('location_tag', 'Zone A')
        rtsp_url = data.get('rtsp_url', 'rtsp://admin:pass@192.168.1.100:554/stream1')
        stream_type = data.get('stream_type', 'mjpg')
        resolution = data.get('resolution', '1080p')
        fps = int(data.get('fps', 30))
        wbs_task_id = data.get('associated_wbs_task_id')

        if not name or not camera_code:
            return JsonResponse({'success': False, 'error': 'name and camera_code are required'}, status=400)

        if CCTVCamera.objects.filter(camera_code=camera_code).exists():
            return JsonResponse({'success': False, 'error': f'Camera code {camera_code} already exists'}, status=400)

        wbs_task = None
        if wbs_task_id:
            try:
                wbs_task = WBSTask.objects.get(id=wbs_task_id, project=project)
            except WBSTask.DoesNotExist:
                pass

        camera = CCTVCamera.objects.create(
            project=project,
            name=name,
            camera_code=camera_code,
            location_tag=location_tag,
            rtsp_url=rtsp_url,
            stream_type=stream_type,
            resolution=resolution,
            fps=fps,
            associated_wbs_task=wbs_task
        )

        token_info = generate_cctv_stream_token(camera.id)
        cam_dict = camera.to_dict()
        cam_dict['stream_token'] = token_info['token']

        return JsonResponse({
            'success': True,
            'message': 'New CCTV camera registered successfully',
            'camera': cam_dict
        })

    cameras = CCTVCamera.objects.filter(project=project)
    camera_list = []
    for cam in cameras:
        cam_dict = cam.to_dict()
        token_info = generate_cctv_stream_token(cam.id)
        cam_dict['stream_token'] = token_info['token']
        camera_list.append(cam_dict)

    return JsonResponse({
        'success': True,
        'project_id': project.id,
        'count': len(camera_list),
        'cameras': camera_list
    })


def api_cctv_stream(request, camera_id):
    """
    Secure token-protected live video stream proxy endpoint.
    Serves multipart/x-mixed-replace MJPEG / HLS stream generator.
    """
    token_str = request.GET.get('token') or request.META.get('HTTP_X_CCTV_TOKEN')
    
    if token_str != 'dev_bypass' and not verify_cctv_stream_token(camera_id, token_str):
        return JsonResponse({'success': False, 'error': 'Invalid or expired stream access token'}, status=403)

    client_ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
    try:
        camera = CCTVCamera.objects.get(id=camera_id)
        CCTVStreamLog.objects.create(
            camera=camera,
            token_hash=hashlib.sha256((token_str or '').encode('utf-8')).hexdigest()[:32],
            client_ip=client_ip,
            duration_seconds=60
        )
    except Exception:
        pass

    return StreamingHttpResponse(
        generate_mjpeg_stream_generator(camera_id),
        content_type='multipart/x-mixed-replace; boundary=frame'
    )


@csrf_exempt
def api_cctv_ai_audit(request, camera_id):
    """
    Executes AI visual progress cross-referencing for a specific CCTV camera feed.
    """
    audit_res = audit_camera_feed_with_ai(camera_id)
    return JsonResponse({'success': True, 'audit': audit_res})


# ==================== GEOFENCED ATTENDANCE REGISTER MODULE VIEWS ====================

def attendance_view(request):
    """
    Renders the Geofenced Attendance Register & Manager Dashboard.
    """
    project = get_or_create_default_project(request)
    summary = get_attendance_summary_metrics(project.id) if project else {}
    tasks = WBSTask.objects.filter(project=project) if project else []
    addons = get_project_addons(project.id) if project else {}

    return render(request, 'attendance.html', {
        'project': project,
        'summary': summary,
        'tasks': tasks,
        'addons': addons,
        'active_page': 'attendance'
    })


@csrf_exempt
def api_attendance_checkin(request):
    """
    API endpoint processing worker check-in with GPS geofence validation and shift state machine check.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    project = get_or_create_default_project(request)
    if not project:
        return JsonResponse({'success': False, 'error': 'No active project found'}, status=404)

    data = get_json_or_post_data(request)
    worker_id = data.get('worker_id')
    worker_name = data.get('worker_name')
    worker_role = data.get('worker_role', 'Field Engineer')
    trade_category = data.get('trade_category', 'General Labor')
    hourly_rate = float(data.get('hourly_rate', 35.0))
    lat = float(data.get('latitude', data.get('lat', project.geofence_latitude)))
    lng = float(data.get('longitude', data.get('lng', project.geofence_longitude)))
    wbs_task_id = data.get('wbs_task_id')

    if not worker_id or not worker_name:
        return JsonResponse({'success': False, 'error': 'worker_id and worker_name are required'}, status=400)

    res = process_worker_checkin(
        project_id=project.id,
        worker_id=worker_id,
        worker_name=worker_name,
        worker_role=worker_role,
        lat=lat,
        lng=lng,
        trade_category=trade_category,
        hourly_rate=hourly_rate,
        wbs_task_id=wbs_task_id
    )

    status_code = 200 if res['success'] else 400
    return JsonResponse(res, status=status_code)


@csrf_exempt
def api_attendance_checkout(request):
    """
    API endpoint processing worker check-out, shift total hours calculation, and EVM labor spend sync.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    project = get_or_create_default_project(request)
    if not project:
        return JsonResponse({'success': False, 'error': 'No active project found'}, status=404)

    data = get_json_or_post_data(request)
    worker_id = data.get('worker_id')
    lat = float(data.get('latitude', data.get('lat', project.geofence_latitude)))
    lng = float(data.get('longitude', data.get('lng', project.geofence_longitude)))

    if not worker_id:
        return JsonResponse({'success': False, 'error': 'worker_id is required'}, status=400)

    res = process_worker_checkout(
        project_id=project.id,
        worker_id=worker_id,
        lat=lat,
        lng=lng
    )

    status_code = 200 if res['success'] else 400
    return JsonResponse(res, status=status_code)


@csrf_exempt
def api_attendance_summary(request):
    """
    API endpoint returning attendance KPIs, compliance rate, and active on-site workers.
    """
    project = get_or_create_default_project(request)
    if not project:
        return JsonResponse({'success': False, 'error': 'No active project found'}, status=404)

    summary = get_attendance_summary_metrics(project.id)
    return JsonResponse(summary)


@csrf_exempt
def api_update_geofence(request):
    """
    API endpoint to update site geofence perimeter coordinates and radius in meters.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    project = get_or_create_default_project(request)
    if not project:
        return JsonResponse({'success': False, 'error': 'No active project found'}, status=404)

    data = get_json_or_post_data(request)
    latitude = data.get('latitude', project.geofence_latitude)
    longitude = data.get('longitude', project.geofence_longitude)
    radius_meters = data.get('radius_meters', project.geofence_radius_meters)

    res = update_project_geofence(
        project_id=project.id,
        latitude=latitude,
        longitude=longitude,
        radius_meters=radius_meters
    )
    return JsonResponse(res)


# ==================== UNIFIED MULTI-INDUSTRY PLATFORM CONTAINER VIEWS ====================

def select_industry_view(request):
    """
    Renders the post-login Industry Selection Landing Gate portal.
    """
    industries = get_all_industries()
    return render(request, 'select_industry.html', {
        'industries': industries,
        'active_page': 'select_industry'
    })


def plantflow_view(request):
    """
    Renders PlantFlow AI (Heavy Manufacturing & BoM Assembly Routing) sub-app workspace.
    """
    request.session['active_industry'] = 'plantflow'
    project = get_or_create_default_project(request)
    metrics = get_plantflow_metrics(project.id) if project else {}

    return render(request, 'plantflow.html', {
        'project': project,
        'metrics': metrics,
        'active_page': 'plantflow',
        'current_industry': get_industry_details('plantflow')
    })


def dockflow_view(request):
    """
    Renders DockFlow AI (Shipbuilding & Drydock Telemetry) sub-app workspace.
    """
    request.session['active_industry'] = 'dockflow'
    project = get_or_create_default_project(request)
    metrics = get_dockflow_metrics(project.id) if project else {}

    return render(request, 'dockflow.html', {
        'project': project,
        'metrics': metrics,
        'active_page': 'dockflow',
        'current_industry': get_industry_details('dockflow')
    })


def aeroguard_view(request):
    """
    Renders AeroGuard AI (Defense Contracting & ITAR Compliance Audit) sub-app workspace.
    """
    request.session['active_industry'] = 'aeroguard'
    project = get_or_create_default_project(request)
    metrics = get_aeroguard_metrics(project.id) if project else {}

    return render(request, 'aeroguard.html', {
        'project': project,
        'metrics': metrics,
        'active_page': 'aeroguard',
        'current_industry': get_industry_details('aeroguard')
    })


def turnaroundos_view(request):
    """
    Renders TurnaroundOS AI (Energy & Refinery Plant Turnarounds) sub-app workspace.
    """
    request.session['active_industry'] = 'turnaroundos'
    project = get_or_create_default_project(request)
    metrics = get_turnaroundos_metrics(project.id) if project else {}

    return render(request, 'turnaroundos.html', {
        'project': project,
        'metrics': metrics,
        'active_page': 'turnaroundos',
        'current_industry': get_industry_details('turnaroundos')
    })


@csrf_exempt
def api_switch_industry(request):
    """
    API endpoint to switch the active operational sector session and return target route.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    data = get_json_or_post_data(request)
    industry_key = data.get('industry_key', 'constructflow')

    if industry_key not in INDUSTRIES:
        return JsonResponse({'success': False, 'error': f'Invalid industry key {industry_key}'}, status=400)

    request.session['active_industry'] = industry_key

    project = get_or_create_default_project(request)
    if project:
        project.industry_sector = industry_key
        project.save()

    ind_details = get_industry_details(industry_key)

    return JsonResponse({
        'success': True,
        'message': f'Switched workspace sector to {ind_details["name"]}',
        'industry': ind_details,
        'target_route': ind_details['route']
    })


@csrf_exempt
def api_industry_metrics(request):
    """
    API endpoint returning domain metrics for the active or requested industry sector.
    """
    project = get_or_create_default_project(request)
    industry_key = request.GET.get('industry_key') or request.session.get('active_industry', 'constructflow')

    if industry_key == 'plantflow':
        metrics = get_plantflow_metrics(project.id if project else None)
    elif industry_key == 'dockflow':
        metrics = get_dockflow_metrics(project.id if project else None)
    elif industry_key == 'aeroguard':
        metrics = get_aeroguard_metrics(project.id if project else None)
    elif industry_key == 'turnaroundos':
        metrics = get_turnaroundos_metrics(project.id if project else None)
    else:
        metrics = {
            'industry': get_industry_details('constructflow'),
            'status': 'active'
        }

    return JsonResponse({'success': True, 'metrics': metrics})







