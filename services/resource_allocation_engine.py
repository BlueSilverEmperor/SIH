import datetime
from core.models import Project, WBSTask, Supplier
from services.supplier_engine import calculate_supplier_scores_and_softmax, get_recommended_supplier_by_category


RESOURCE_BUNDLES = {
    '1.1': {
        'crew_name': 'Heavy Excavation Crew A (6 Operators)',
        'machinery': 'CAT 320 Crawler Excavator + 3 Dump Trucks',
        'category': 'General'
    },
    '1.2': {
        'crew_name': 'Concrete Base Pouring Unit #4 (10 Workers)',
        'machinery': 'Putzmeister Concrete Pump Truck + Batching Plant',
        'category': 'Concrete'
    },
    '1.3': {
        'crew_name': 'Superstructure Steel Rebar Fitters (8 Ironworkers)',
        'machinery': '50t Tower Crane + Hydraulic Rebar Benders',
        'category': 'Steel Rebar'
    },
    '2.1': {
        'crew_name': 'Block Masonry Crew #2 (8 Masons)',
        'machinery': 'Mortar Mixer + Scaffolding Rig System',
        'category': 'Masonry'
    },
    '3.1': {
        'crew_name': 'Certified MEP Engineering Team (6 Technicians)',
        'machinery': 'Conduit Benders + Pressure Testing Kit',
        'category': 'Electrical'
    }
}


def allocate_resources_and_suppliers_for_project(project_id):
    """
    Intelligent Resource Ordering & Allocation Engine.
    Assigns labor crews, heavy machinery, and material suppliers to each project phase
    based on blueprint takeoffs and Softmax supplier probabilities.
    """
    project = Project.objects.filter(id=project_id).first()
    if not project:
        return {'success': False, 'error': 'Project not found'}

    # 1. Run Softmax Supplier Scoring across all categories
    calculate_supplier_scores_and_softmax(project_id=project_id)
    recommendations_res = get_recommended_supplier_by_category(project_id=project_id)
    rec_suppliers = recommendations_res.get('recommendations', {}) if isinstance(recommendations_res, dict) else {}

    tasks = list(WBSTask.objects.filter(project_id=project_id))
    allocated_tasks = []

    for task in tasks:
        bundle = None
        for code_prefix, b in RESOURCE_BUNDLES.items():
            if task.wbs_code.startswith(code_prefix) or code_prefix in task.wbs_code:
                bundle = b
                break
        
        if not bundle:
            bundle = {
                'crew_name': 'General Construction Workgroup',
                'machinery': 'Standard Site Tools',
                'category': 'General'
            }

        # Find best supplier for category
        cat = bundle['category']
        sup_dict = rec_suppliers.get(cat)
        sup_obj = None
        if sup_dict:
            sup_obj = Supplier.objects.filter(id=sup_dict['id']).first()
        if not sup_obj:
            sup_obj = Supplier.objects.filter(category=cat).order_by('-softmax_probability').first()
        if not sup_obj:
            sup_obj = Supplier.objects.first()

        # Bind supplier to WBSTask
        if sup_obj:
            task.assigned_supplier = sup_obj
            task.save()

        allocated_tasks.append({
            'wbs_code': task.wbs_code,
            'task_name': task.task_name,
            'crew_name': bundle['crew_name'],
            'machinery': bundle['machinery'],
            'assigned_supplier': sup_obj.name if sup_obj else 'Unassigned',
            'supplier_category': cat,
            'softmax_score': round(sup_obj.softmax_probability * 100.0, 1) if sup_obj else 0.0
        })

    return {
        'success': True,
        'project_id': project_id,
        'allocated_tasks_count': len(allocated_tasks),
        'resource_matrix': allocated_tasks
    }
