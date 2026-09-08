import datetime
from django.utils import timezone
from core.models import Project, WBSTask, DailyProgressAudit
from services.addon_manager import is_addon_enabled


def run_daily_progress_audit(project_id):
    """
    Add-On 3: Daily Progress Tracker & Audit Service.
    Audits daily field progress against planned velocity and logs results into DailyProgressAudit.
    """
    # Check if Add-On 3 is enabled
    if not is_addon_enabled(project_id, 'daily_progress_audit'):
        return {
            'enabled': False,
            'message': 'Daily Progress Tracker Add-On is disabled.',
            'audits': []
        }

    project = Project.objects.filter(id=project_id).first()
    if not project:
        return {'enabled': True, 'error': 'Project not found'}

    tasks = WBSTask.objects.filter(project_id=project_id)
    today = datetime.date.today()

    start_date = project.start_date or datetime.date(2026, 1, 15)
    target_end_date = project.target_end_date or datetime.date(2026, 12, 30)
    baseline_duration_days = max(30, (target_end_date - start_date).days)
    elapsed_days = max(1, (today - start_date).days)

    total_planned_qty = sum(t.planned_quantity for t in tasks)
    total_actual_qty = sum(t.actual_quantity for t in tasks)

    planned_velocity = round(total_planned_qty / baseline_duration_days, 2) if baseline_duration_days > 0 else 0.0
    actual_velocity = round(total_actual_qty / elapsed_days, 2) if elapsed_days > 0 else 0.0

    velocity_variance = round(actual_velocity - planned_velocity, 2)

    if velocity_variance >= -0.05:
        audit_status = 'on_track'
        notes = f"Daily field velocity ({actual_velocity} u/d) meets target ({planned_velocity} u/d)."
    elif velocity_variance >= -0.20:
        audit_status = 'minor_delay'
        notes = f"Daily field velocity ({actual_velocity} u/d) is slightly below target ({planned_velocity} u/d)."
    else:
        audit_status = 'critical_delay'
        notes = f"Daily field velocity ({actual_velocity} u/d) critically lags target ({planned_velocity} u/d)."

    # Log into DailyProgressAudit
    audit, created = DailyProgressAudit.objects.get_or_create(
        project=project,
        audit_date=today,
        defaults={
            'planned_velocity': planned_velocity,
            'actual_velocity': actual_velocity,
            'variance': velocity_variance,
            'audit_status': audit_status,
            'notes': notes
        }
    )
    if not created:
        audit.planned_velocity = planned_velocity
        audit.actual_velocity = actual_velocity
        audit.variance = velocity_variance
        audit.audit_status = audit_status
        audit.notes = notes
        audit.save()

    history = get_daily_audit_history(project_id)

    return {
        'enabled': True,
        'today_audit': audit.to_dict(),
        'planned_velocity': planned_velocity,
        'actual_velocity': actual_velocity,
        'variance': velocity_variance,
        'audit_status': audit_status,
        'notes': notes,
        'history': history
    }


def get_daily_audit_history(project_id, limit=14):
    """
    Retrieves daily audit history for UI charts & reporting.
    """
    audits = DailyProgressAudit.objects.filter(project_id=project_id).order_by('-audit_date')[:limit]
    return [a.to_dict() for a in audits]
