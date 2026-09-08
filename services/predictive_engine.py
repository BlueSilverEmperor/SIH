import datetime
from core.models import Project, WBSTask, Supplier
from services.supplier_engine import calculate_supplier_scores_and_softmax

def calculate_predictive_completion(project_id):
    """
    Real-Time Predictive Completion Engine.
    Calculates:
    1. Planned Daily Velocity (V_planned = Total Planned Work / Baseline Duration Days)
    2. Actual Live Field Velocity (V_actual = Total Completed Work / Elapsed Days)
    3. Schedule Performance Index (SPI = EV / PV)
    4. Remaining Work Forecast Days:
       D_forecast = Remaining Work / max(0.1, V_actual * SPI)
    5. Supplier Risk Buffer (Risk_buffer_days):
       Evaluates critical path tasks assigned suppliers. If Softmax probability < 0.25
       or delivery score < 70%, appends +3 to +10 days buffer.
    6. AI-Forecasted Completion Date = Current Date + D_forecast + Risk_buffer_days
    7. Schedule Variance Days = AI-Forecasted Completion Date - Target End Date
    """
    project = Project.objects.filter(id=project_id).first()
    if not project:
        return None

    tasks = list(WBSTask.objects.filter(project_id=project_id))
    today = datetime.date.today()
    start_date = project.start_date or datetime.date(2026, 1, 15)
    target_end_date = project.target_end_date or datetime.date(2026, 12, 30)

    baseline_duration_days = max(30, (target_end_date - start_date).days)
    elapsed_days = max(1, (today - start_date).days)

    total_pv = sum(t.planned_value for t in tasks)
    total_ev = sum(t.earned_value for t in tasks)
    total_ac = sum(t.actual_cost for t in tasks)

    total_planned_qty = sum(t.planned_quantity for t in tasks)
    total_actual_qty = sum(t.actual_quantity for t in tasks)
    total_remaining_qty = max(0.0, total_planned_qty - total_actual_qty)

    spi = round(total_ev / total_pv, 3) if total_pv > 0 else 1.0

    # 1. Planned Velocity & Actual Field Velocity (units/day)
    planned_velocity = round(total_planned_qty / baseline_duration_days, 2)
    actual_velocity = round(total_actual_qty / elapsed_days, 2)

    # Baseline velocity fallback when live actual field output is 0.0
    if actual_velocity > 0:
        effective_velocity = max(0.1, round(actual_velocity * max(0.2, spi), 2))
    else:
        effective_velocity = max(0.1, round(planned_velocity * max(0.2, spi), 2))

    # 2. Remaining Forecast Days
    if total_remaining_qty <= 0:
        forecast_remaining_days = 0
    else:
        forecast_remaining_days = int(round(total_remaining_qty / effective_velocity))

    # 3. Supplier Risk-Adjusted Buffer Projections
    supplier_risk_buffer_days = 0
    supplier_risk_notes = []

    critical_tasks = [t for t in tasks if t.is_critical_path]
    for task in critical_tasks:
        if task.assigned_supplier:
            sup = task.assigned_supplier
            if sup.softmax_probability < 0.25 or sup.delivery_score < 70.0:
                buffer = int(round((1.0 - sup.softmax_probability) * 8))
                supplier_risk_buffer_days += buffer
                supplier_risk_notes.append(
                    f"Task '{task.task_name}' assigned to {sup.name} (Delivery: {sup.delivery_score}/100, Softmax: {round(sup.softmax_probability*100,1)}%) -> +{buffer}d Risk Buffer"
                )

    # 4. Total Forecasted End Date
    total_remaining_days = forecast_remaining_days + supplier_risk_buffer_days
    forecasted_end_date = today + datetime.timedelta(days=total_remaining_days)

    # 5. Schedule Variance Days (Relative to Target End Date)
    schedule_variance_days = (forecasted_end_date - target_end_date).days

    # 6. Predictive Status Classification
    if schedule_variance_days > 14:
        predictive_status = 'critical_slip'
    elif schedule_variance_days > 3:
        predictive_status = 'delayed'
    elif schedule_variance_days < -3:
        predictive_status = 'accelerated'
    else:
        predictive_status = 'on_track'

    # Update Project DB fields
    project.baseline_duration_days = baseline_duration_days
    project.forecasted_end_date = forecasted_end_date
    project.schedule_variance_days = schedule_variance_days
    project.field_velocity_rate = actual_velocity
    project.supplier_risk_buffer_days = supplier_risk_buffer_days
    project.predictive_status = predictive_status
    project.save()

    return {
        'project_id': project_id,
        'start_date': start_date.isoformat(),
        'target_end_date': target_end_date.isoformat(),
        'forecasted_end_date': forecasted_end_date.isoformat(),
        'baseline_duration_days': baseline_duration_days,
        'elapsed_days': elapsed_days,
        'remaining_forecast_days': forecast_remaining_days,
        'supplier_risk_buffer_days': supplier_risk_buffer_days,
        'supplier_risk_notes': supplier_risk_notes,
        'schedule_variance_days': schedule_variance_days,
        'variance_label': f"+{schedule_variance_days} Days Behind" if schedule_variance_days > 0 else (f"{schedule_variance_days} Days Ahead" if schedule_variance_days < 0 else "On Track"),
        'planned_velocity': planned_velocity,
        'actual_velocity': actual_velocity,
        'effective_velocity': effective_velocity,
        'spi': spi,
        'predictive_status': predictive_status,
        'total_planned_qty': total_planned_qty,
        'total_actual_qty': total_actual_qty,
        'total_remaining_qty': total_remaining_qty
    }
