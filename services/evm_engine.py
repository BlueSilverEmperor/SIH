import datetime
from core.models import Project, WBSTask, FieldInput, ExtractedMetric, AnalyticsLog

def calculate_project_evm(project_id):
    """
    Calculates total PV, EV, AC, SV, CV, SPI, and CPI for a project
    and records an AnalyticsLog snapshot.
    """
    project = Project.objects.filter(id=project_id).first()
    if not project:
        return None

    tasks = list(WBSTask.objects.filter(project_id=project_id))

    total_pv = 0.0
    total_ev = 0.0
    total_ac = 0.0

    for task in tasks:
        task.calculate_evm()
        task.save()
        total_pv += task.planned_value
        total_ev += task.earned_value
        total_ac += task.actual_cost

    schedule_variance = total_ev - total_pv
    cost_variance = total_ev - total_ac

    spi = round(total_ev / total_pv, 3) if total_pv > 0 else 1.0
    cpi = round(total_ev / total_ac, 3) if total_ac > 0 else 1.0

    # Extended Forecasting: BAC, EAC, ETC, VAC & Profit Margin
    bac = float(project.total_budget) if project.total_budget and project.total_budget > 0 else sum(t.planned_value for t in tasks)
    eac = round(bac / cpi, 2) if cpi > 0 else bac
    etc = round(max(0.0, eac - total_ac), 2)
    vac = round(bac - eac, 2)
    projected_margin_pct = round(((bac - eac) / bac) * 100.0, 2) if bac > 0 else 0.0

    # Threshold alerts
    spi_status = 'critical' if spi < 0.85 else ('warning' if spi < 0.95 else 'optimal')
    cpi_status = 'critical' if cpi < 0.85 else ('warning' if cpi < 0.95 else 'optimal')

    if spi < 0.90 and cpi < 0.90:
        alert_level = 'danger'
        alert_msg = 'Critical Delay & Budget Overrun Warning!'
    elif spi < 0.90:
        alert_level = 'warning'
        alert_msg = 'Schedule Slippage Warning: Project behind planned pace.'
    elif cpi < 0.90:
        alert_level = 'warning'
        alert_msg = 'Cost Variance Warning: Actual spending exceeds earned value.'
    else:
        alert_level = 'success'
        alert_msg = 'Project performing within baseline schedule & budget parameters.'

    # Log analytics snapshot
    log_entry = AnalyticsLog.objects.create(
        project=project,
        snapshot_date=datetime.datetime.utcnow(),
        total_pv=total_pv,
        total_ev=total_ev,
        total_ac=total_ac,
        schedule_variance=schedule_variance,
        cost_variance=cost_variance,
        spi=spi,
        cpi=cpi,
        notes=f"EVM auto-recalculated for project {project.code}"
    )

    # Calculate predictive completion time & velocity forecast
    from services.predictive_engine import calculate_predictive_completion
    predictive_data = calculate_predictive_completion(project_id)

    return {
        'project_id': project_id,
        'total_pv': round(total_pv, 2),
        'total_ev': round(total_ev, 2),
        'total_ac': round(total_ac, 2),
        'schedule_variance': round(schedule_variance, 2),
        'cost_variance': round(cost_variance, 2),
        'spi': spi,
        'cpi': cpi,
        'bac': round(bac, 2),
        'eac': round(eac, 2),
        'etc': round(etc, 2),
        'vac': round(vac, 2),
        'projected_margin_pct': projected_margin_pct,
        'spi_status': spi_status,
        'cpi_status': cpi_status,
        'alert_level': alert_level,
        'alert_msg': alert_msg,
        'task_count': len(tasks),
        'predictive': predictive_data
    }


def approve_and_sync_metric(extracted_metric_id, target_wbs_task_id=None, override_quantity=None, override_cost=None):
    """
    Approve an extracted metric and synchronize it with the Master WBS Task.
    Updates WBS task actual quantity, EV, AC, and completion percentage.
    """
    metric = ExtractedMetric.objects.filter(id=extracted_metric_id).first()
    if not metric:
        raise ValueError(f"ExtractedMetric with ID {extracted_metric_id} not found.")

    wbs_task_id = target_wbs_task_id or metric.wbs_task_id
    if not wbs_task_id:
        raise ValueError("No WBS Task associated or selected for this extraction.")

    task = WBSTask.objects.filter(id=wbs_task_id).first()
    if not task:
        raise ValueError(f"WBSTask with ID {wbs_task_id} not found.")

    qty_to_add = float(override_quantity) if override_quantity is not None else metric.extracted_quantity
    cost_to_add = float(override_cost) if override_cost is not None else metric.incurred_cost

    # Update Task metrics
    task.actual_quantity += qty_to_add
    task.actual_cost += cost_to_add
    task.calculate_evm()
    task.save()

    # Update Metric status and association
    metric.wbs_task = task
    metric.status = 'approved'
    if override_quantity is not None:
        metric.extracted_quantity = qty_to_add
    if override_cost is not None:
        metric.incurred_cost = cost_to_add
    metric.save()

    # Update parent FieldInput status
    field_input = FieldInput.objects.filter(id=metric.field_input_id).first()
    if field_input:
        field_input.status = 'approved'
        field_input.save()

    # Trigger project-level EVM sync
    evm_summary = calculate_project_evm(task.project_id)
    return {
        'metric_id': metric.id,
        'wbs_task_id': task.id,
        'updated_task': task.to_dict(),
        'project_evm': evm_summary
    }


def reject_metric(extracted_metric_id, reasoning=None):
    """
    Rejects an extracted metric.
    """
    metric = ExtractedMetric.objects.filter(id=extracted_metric_id).first()
    if not metric:
        raise ValueError("Extracted metric not found.")

    metric.status = 'rejected'
    if reasoning:
        metric.ai_reasoning = (metric.ai_reasoning or '') + f" [Rejected: {reasoning}]"
    metric.save()

    field_input = FieldInput.objects.filter(id=metric.field_input_id).first()
    if field_input:
        field_input.status = 'rejected'
        field_input.save()

    return metric.to_dict()
