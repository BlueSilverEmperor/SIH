import math
import datetime
from django.utils import timezone
from core.models import Project, AttendanceRecord, WBSTask
from services.evm_engine import calculate_project_evm


def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculates the great-circle distance between two GPS coordinates in meters using Haversine formula.
    """
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return R * c


def process_worker_checkin(project_id, worker_id, worker_name, worker_role='Field Engineer', lat=37.7749, lng=-122.4194, trade_category='General Labor', hourly_rate=35.0, wbs_task_id=None):
    """
    Processes worker check-in request with server-side GPS geofence validation and shift state machine check.
    """
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return {'success': False, 'error': f'Project #{project_id} not found'}

    # 1. State Machine: Duplicate Check-In Prevention
    active_record = AttendanceRecord.objects.filter(
        project=project,
        worker_id=worker_id,
        shift_status='ACTIVE_ON_SITE'
    ).first()

    if active_record:
        return {
            'success': False,
            'error': f'Worker {worker_name} ({worker_id}) is already checked in and active on site since {active_record.checkin_time.strftime("%H:%M:%S")}.',
            'record': active_record.to_dict()
        }

    # 2. Server-Side Geofence Distance Validation
    distance_m = calculate_haversine_distance(
        float(lat), float(lng),
        project.geofence_latitude, project.geofence_longitude
    )
    is_valid = distance_m <= project.geofence_radius_meters

    status = 'verified' if is_valid else 'out_of_bounds'
    shift_status = 'ACTIVE_ON_SITE' if is_valid else 'OUT_OF_BOUNDS'

    wbs_task = None
    if wbs_task_id:
        try:
            wbs_task = WBSTask.objects.get(id=wbs_task_id, project=project)
        except WBSTask.DoesNotExist:
            pass

    # 3. Create Attendance Record
    record = AttendanceRecord.objects.create(
        project=project,
        worker_id=worker_id,
        worker_name=worker_name,
        worker_role=worker_role,
        trade_category=trade_category,
        hourly_rate=float(hourly_rate),
        shift_type='morning_checkin',
        checkin_time=timezone.now(),
        latitude=float(lat),
        longitude=float(lng),
        distance_from_center_m=round(distance_m, 1),
        checkin_lat=float(lat),
        checkin_lng=float(lng),
        checkin_distance_m=round(distance_m, 1),
        is_geofence_valid=is_valid,
        status=status,
        shift_status=shift_status,
        associated_wbs_task=wbs_task
    )

    return {
        'success': True,
        'message': 'Worker check-in verified & logged successfully' if is_valid else 'Check-in flagged: Worker GPS is outside project geofence boundary.',
        'is_geofence_valid': is_valid,
        'distance_from_center_m': round(distance_m, 1),
        'geofence_radius_m': project.geofence_radius_meters,
        'record': record.to_dict()
    }


def process_worker_checkout(project_id, worker_id, lat=37.7749, lng=-122.4194):
    """
    Processes worker check-out request, calculates total shift hours and labor spend,
    and updates WBS task actual costs and EVM analytics.
    """
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return {'success': False, 'error': f'Project #{project_id} not found'}

    # 1. Locate active check-in session
    record = AttendanceRecord.objects.filter(
        project=project,
        worker_id=worker_id,
        shift_status='ACTIVE_ON_SITE'
    ).first()

    if not record:
        return {
            'success': False,
            'error': f'No active check-in session found for worker ID {worker_id}. Check-in is required before checking out.'
        }

    # 2. Server-side Geofence distance calculation for checkout
    distance_m = calculate_haversine_distance(
        float(lat), float(lng),
        project.geofence_latitude, project.geofence_longitude
    )

    now = timezone.now()
    record.checkout_time = now
    record.checkout_lat = float(lat)
    record.checkout_lng = float(lng)
    record.checkout_distance_m = round(distance_m, 1)
    record.shift_type = 'evening_checkout'
    record.shift_status = 'COMPLETED'

    # Calculate duration & labor cost
    duration_hrs, labor_cost = record.calculate_shift_totals()
    record.save()

    # 3. Direct EVM & WBS Labor Budget Pipeline Integration
    wbs_task = record.associated_wbs_task
    if not wbs_task:
        # Fallback to critical path or first active task
        wbs_task = WBSTask.objects.filter(project=project, is_critical_path=True).first() or WBSTask.objects.filter(project=project).first()

    evm_synced = False
    if wbs_task and labor_cost > 0:
        wbs_task.actual_cost = round(wbs_task.actual_cost + labor_cost, 2)
        wbs_task.calculate_evm()
        wbs_task.save()
        calculate_project_evm(project.id)
        evm_synced = True

    return {
        'success': True,
        'message': f'Worker {record.worker_name} checked out. Shift duration: {duration_hrs} hrs (${labor_cost}).',
        'shift_duration_hours': duration_hrs,
        'labor_cost': labor_cost,
        'evm_synced': evm_synced,
        'associated_task_name': wbs_task.task_name if wbs_task else None,
        'record': record.to_dict()
    }


def update_project_geofence(project_id, latitude, longitude, radius_meters=200.0):
    """
    Updates site geofence perimeter coordinates and radius in meters.
    """
    try:
        project = Project.objects.get(id=project_id)
        project.geofence_latitude = float(latitude)
        project.geofence_longitude = float(longitude)
        project.geofence_radius_meters = float(radius_meters)
        project.save()
        return {
            'success': True,
            'message': 'Project site geofence boundary updated successfully',
            'geofence_latitude': project.geofence_latitude,
            'geofence_longitude': project.geofence_longitude,
            'geofence_radius_meters': project.geofence_radius_meters
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_attendance_summary_metrics(project_id):
    """
    Calculates summary KPIs and active register lists for manager dashboard.
    """
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return {'success': False, 'error': 'Project not found'}

    all_records = AttendanceRecord.objects.filter(project=project).order_by('-timestamp')
    active_workers = all_records.filter(shift_status='ACTIVE_ON_SITE')
    completed_today = all_records.filter(shift_status='COMPLETED')

    total_records_count = all_records.count()
    verified_count = all_records.filter(status='verified').count()
    out_of_bounds_count = all_records.filter(status='out_of_bounds').count()

    compliance_rate = round((verified_count / max(1, total_records_count)) * 100.0, 1)

    total_hours_today = round(sum(r.shift_duration_hours for r in all_records), 1)
    total_labor_spend = round(sum(r.labor_cost for r in all_records), 2)

    return {
        'success': True,
        'project_id': project.id,
        'project_name': project.name,
        'geofence_latitude': project.geofence_latitude,
        'geofence_longitude': project.geofence_longitude,
        'geofence_radius_meters': project.geofence_radius_meters,
        'active_on_site_count': active_workers.count(),
        'completed_shifts_count': completed_today.count(),
        'total_records_count': total_records_count,
        'compliance_rate_pct': compliance_rate,
        'out_of_bounds_count': out_of_bounds_count,
        'total_hours_logged': total_hours_today,
        'total_labor_spend_dollars': total_labor_spend,
        'active_workers': [r.to_dict() for r in active_workers],
        'recent_logs': [r.to_dict() for r in all_records[:20]]
    }
