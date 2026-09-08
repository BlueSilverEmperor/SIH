import datetime
from core.models import Project, WBSTask


UNIT_RATES = {
    'excavation': {'total': 35.0, 'labor': 15.0, 'material': 20.0, 'unit': 'cu.m'},
    'concrete': {'total': 160.0, 'labor': 45.0, 'material': 115.0, 'unit': 'cu.m'},
    'steel': {'total': 950.0, 'labor': 250.0, 'material': 700.0, 'unit': 'tons'},
    'masonry': {'total': 52.0, 'labor': 22.0, 'material': 30.0, 'unit': 'sq.m'},
    'mep': {'total': 28.0, 'labor': 16.0, 'material': 12.0, 'unit': 'm'}
}


def calculate_blueprint_cost_and_takeoffs(project_id, parsed_specs):
    """
    Automated Blueprint Cost & Material Estimation Engine.
    Calculates material takeoffs (concrete, steel, masonry, MEP) and computes estimated material and labor costs.
    Updates project tasks and budget.
    """
    project = Project.objects.filter(id=project_id).first()
    if not project:
        return {'success': False, 'error': 'Project not found'}

    slab_area = float(parsed_specs.get('slab_area', 450.0))
    wall_count = int(parsed_specs.get('wall_count', 16))
    column_count = int(parsed_specs.get('column_count', 20))
    stories = int(parsed_specs.get('stories', 2))
    building_type = parsed_specs.get('building_type', 'commercial_building')

    # 1. Calculate Structural Material Takeoffs
    excavation_qty = round(slab_area * 1.4, 1)
    concrete_qty = round(slab_area * 0.42 * stories, 1)
    steel_qty = round(concrete_qty * 0.11, 1)
    masonry_qty = round(wall_count * 32.0 * stories, 1)
    mep_qty = round(slab_area * 1.6 * stories, 1)

    # 2. Compute Itemized Costs
    cost_excavation = excavation_qty * UNIT_RATES['excavation']['total']
    cost_concrete = concrete_qty * UNIT_RATES['concrete']['total']
    cost_steel = steel_qty * UNIT_RATES['steel']['total']
    cost_masonry = masonry_qty * UNIT_RATES['masonry']['total']
    cost_mep = mep_qty * UNIT_RATES['mep']['total']

    total_material_cost = (
        (excavation_qty * UNIT_RATES['excavation']['material']) +
        (concrete_qty * UNIT_RATES['concrete']['material']) +
        (steel_qty * UNIT_RATES['steel']['material']) +
        (masonry_qty * UNIT_RATES['masonry']['material']) +
        (mep_qty * UNIT_RATES['mep']['material'])
    )

    total_labor_cost = (
        (excavation_qty * UNIT_RATES['excavation']['labor']) +
        (concrete_qty * UNIT_RATES['concrete']['labor']) +
        (steel_qty * UNIT_RATES['steel']['labor']) +
        (masonry_qty * UNIT_RATES['masonry']['labor']) +
        (mep_qty * UNIT_RATES['mep']['labor'])
    )

    total_estimated_budget = round(total_material_cost + total_labor_cost, 2)

    # 3. Create or Update Project WBS Tasks
    wbs_items = [
        {
            "wbs_code": "1.1",
            "task_name": "Site Excavation & Foundation Trenching",
            "planned_qty": excavation_qty,
            "unit": UNIT_RATES['excavation']['unit'],
            "unit_cost": UNIT_RATES['excavation']['total'],
            "critical": True,
            "milestone": "Substructure Clearance"
        },
        {
            "wbs_code": "1.2",
            "task_name": "Structural Concrete Base & Slab Pouring",
            "planned_qty": concrete_qty,
            "unit": UNIT_RATES['concrete']['unit'],
            "unit_cost": UNIT_RATES['concrete']['total'],
            "critical": True,
            "milestone": "Substructure Concrete Base"
        },
        {
            "wbs_code": "1.3",
            "task_name": "Superstructure Steel Rebar & Column Frame",
            "planned_qty": steel_qty,
            "unit": UNIT_RATES['steel']['unit'],
            "unit_cost": UNIT_RATES['steel']['total'],
            "critical": True,
            "milestone": "Superstructure Frame"
        },
        {
            "wbs_code": "2.1",
            "task_name": "Exterior Block Masonry & Enclosure",
            "planned_qty": masonry_qty,
            "unit": UNIT_RATES['masonry']['unit'],
            "unit_cost": UNIT_RATES['masonry']['total'],
            "critical": False,
            "milestone": "Building Envelope Closure"
        },
        {
            "wbs_code": "3.1",
            "task_name": "MEP Electrical & Plumbing Distribution",
            "planned_qty": mep_qty,
            "unit": UNIT_RATES['mep']['unit'],
            "unit_cost": UNIT_RATES['mep']['total'],
            "critical": False,
            "milestone": "MEP Energization"
        }
    ]

    start_d = project.start_date or datetime.date.today()
    end_d = project.target_end_date or (start_d + datetime.timedelta(days=180))

    # Update or insert WBS tasks
    created_tasks = []
    for item in wbs_items:
        task, created = WBSTask.objects.get_or_create(
            project=project,
            wbs_code=item["wbs_code"],
            defaults={
                "task_name": item["task_name"],
                "planned_quantity": item["planned_qty"],
                "actual_quantity": 0.0,
                "unit": item["unit"],
                "unit_cost": item["unit_cost"],
                "planned_start_date": start_d,
                "planned_end_date": end_d,
                "is_critical_path": item["critical"],
                "milestone_name": item["milestone"]
            }
        )
        if not created:
            task.task_name = item["task_name"]
            task.planned_quantity = item["planned_qty"]
            task.unit = item["unit"]
            task.unit_cost = item["unit_cost"]
            task.is_critical_path = item["critical"]
            task.milestone_name = item["milestone"]
            task.calculate_evm()
            task.save()
        else:
            task.calculate_evm()
            task.save()
        created_tasks.append(task.to_dict())

    # Update Project Total Budget
    project.total_budget = total_estimated_budget
    project.save()

    return {
        'success': True,
        'project_id': project.id,
        'building_type': building_type,
        'stories': stories,
        'takeoffs': {
            'excavation_qty_cum': excavation_qty,
            'concrete_qty_cum': concrete_qty,
            'steel_qty_tons': steel_qty,
            'masonry_qty_sqm': masonry_qty,
            'mep_qty_m': mep_qty
        },
        'financials': {
            'total_material_cost': round(total_material_cost, 2),
            'total_labor_cost': round(total_labor_cost, 2),
            'total_estimated_budget': total_estimated_budget
        },
        'tasks_count': len(created_tasks)
    }
