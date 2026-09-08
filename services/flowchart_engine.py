import json
import datetime
from core.models import Project, WBSTask, FailSafeReorgLog
from services.addon_manager import is_addon_enabled


STANDARD_PHASE_DEFINITIONS = [
    {
        'id': 'phase_0',
        'step_number': 1,
        'title': 'Pre-Construction & Site Approvals',
        'icon': 'clipboard-check',
        'wbs_prefix': ['0', '1.0']
    },
    {
        'id': 'phase_1',
        'step_number': 2,
        'title': 'Excavation & Substructure Base',
        'icon': 'trowel-bricks',
        'wbs_prefix': ['1.1']
    },
    {
        'id': 'phase_2',
        'step_number': 3,
        'title': 'Concrete Base & Steel Superstructure',
        'icon': 'building',
        'wbs_prefix': ['1.2', '1.3']
    },
    {
        'id': 'phase_3',
        'step_number': 4,
        'title': 'Block Masonry & Building Envelope',
        'icon': 'layer-group',
        'wbs_prefix': ['2.1', '2.2']
    },
    {
        'id': 'phase_4',
        'step_number': 5,
        'title': 'MEP Electrical & Plumbing Services',
        'icon': 'bolt',
        'wbs_prefix': ['3.1', '3.2']
    },
    {
        'id': 'phase_5',
        'step_number': 6,
        'title': 'Final Inspection & Commissioning',
        'icon': 'flag-checkered',
        'wbs_prefix': ['4.1', '4.2', '5.1']
    }
]


def generate_project_flowchart(project_id):
    """
    Add-On 5: Interactive Visual Pipeline & Flowchart Workflow Generator.
    Converts project WBS tasks and phases into a connected sequence of flowchart nodes & edges.
    Binds real-time task progress and fail-safe emergency re-routing badges.
    """
    if not is_addon_enabled(project_id, 'visual_flowchart_workflow'):
        return {
            'enabled': False,
            'message': 'Visual Flowchart Workflow Add-On is disabled for this project.',
            'nodes': [],
            'edges': []
        }

    project = Project.objects.filter(id=project_id).first()
    if not project:
        return {'enabled': True, 'error': 'Project not found', 'nodes': [], 'edges': []}

    tasks = list(WBSTask.objects.filter(project_id=project_id).order_by('wbs_code'))
    failsafe_logs = list(FailSafeReorgLog.objects.filter(project_id=project_id).order_by('-trigger_date'))

    # Extract crashed task WBS codes from fail-safe logs
    crashed_wbs_map = {}
    for log in failsafe_logs:
        details = log.to_dict().get('details', [])
        for item in details:
            code = item.get('wbs_code')
            if code and code not in crashed_wbs_map:
                crashed_wbs_map[code] = item

    nodes = []
    task_assignments = set()

    # Build Phase Nodes
    for phase_def in STANDARD_PHASE_DEFINITIONS:
        matched_tasks = []
        for t in tasks:
            for prefix in phase_def['wbs_prefix']:
                if t.wbs_code.startswith(prefix) or prefix in t.wbs_code:
                    matched_tasks.append(t)
                    task_assignments.add(t.id)
                    break

        # Fallback if no specific tasks matched
        if not matched_tasks and phase_def['step_number'] == 1:
            matched_tasks = [t for t in tasks if t.wbs_code == '1.1']

        t_planned_qty = sum(t.planned_quantity for t in matched_tasks)
        t_actual_qty = sum(t.actual_quantity for t in matched_tasks)

        if t_planned_qty > 0:
            progress_pct = min(100.0, round((t_actual_qty / t_planned_qty) * 100.0, 1))
        else:
            progress_pct = 100.0 if all(t.completion_percentage >= 100 for t in matched_tasks) and matched_tasks else 0.0

        # Determine Node Status
        is_crashed = False
        crashed_info = None
        for t in matched_tasks:
            if t.wbs_code in crashed_wbs_map:
                is_crashed = True
                crashed_info = crashed_wbs_map[t.wbs_code]
                break

        if progress_pct >= 100.0:
            status = 'completed'
        elif is_crashed:
            status = 'critical_crashed'
        elif progress_pct > 0.0:
            status = 'in_progress'
        else:
            status = 'pending'

        start_dates = [t.planned_start_date for t in matched_tasks if t.planned_start_date]
        end_dates = [t.planned_end_date for t in matched_tasks if t.planned_end_date]
        
        nodes.append({
            'id': phase_def['id'],
            'step_number': phase_def['step_number'],
            'title': phase_def['title'],
            'icon': phase_def['icon'],
            'wbs_codes': [t.wbs_code for t in matched_tasks],
            'task_count': len(matched_tasks),
            'progress_pct': progress_pct,
            'status': status,
            'is_crashed': is_crashed,
            'crashed_info': crashed_info,
            'planned_start': min(start_dates).isoformat() if start_dates else None,
            'planned_end': max(end_dates).isoformat() if end_dates else None,
            'tasks': [t.to_dict() for t in matched_tasks]
        })

    # Catch remaining unassigned tasks into an additional Phase Node if any
    unassigned_tasks = [t for t in tasks if t.id not in task_assignments]
    if unassigned_tasks:
        u_planned = sum(t.planned_quantity for t in unassigned_tasks)
        u_actual = sum(t.actual_quantity for t in unassigned_tasks)
        u_prog = min(100.0, round((u_actual / u_planned) * 100.0, 1)) if u_planned > 0 else 0.0
        
        nodes.append({
            'id': 'phase_custom',
            'step_number': len(nodes) + 1,
            'title': 'Specialized Work Items',
            'icon': 'screwdriver-wrench',
            'wbs_codes': [t.wbs_code for t in unassigned_tasks],
            'task_count': len(unassigned_tasks),
            'progress_pct': u_prog,
            'status': 'completed' if u_prog >= 100 else ('in_progress' if u_prog > 0 else 'pending'),
            'is_crashed': False,
            'crashed_info': None,
            'planned_start': None,
            'planned_end': None,
            'tasks': [t.to_dict() for t in unassigned_tasks]
        })

    # Build Connecting Edges
    edges = []
    for i in range(len(nodes) - 1):
        curr_node = nodes[i]
        next_node = nodes[i + 1]

        edge_type = 'normal'
        edge_label = 'Precedes'

        if curr_node['is_crashed'] or next_node['is_crashed']:
            edge_type = 'crashed_reroute'
            edge_label = 'Fail-Safe Fast-Track Arrow (-3d Enforced)'

        is_active = (curr_node['status'] == 'completed' or curr_node['status'] == 'in_progress')

        edges.append({
            'id': f"edge_{curr_node['id']}_{next_node['id']}",
            'source': curr_node['id'],
            'target': next_node['id'],
            'type': edge_type,
            'label': edge_label,
            'is_active': is_active
        })

    completed_count = sum(1 for n in nodes if n['status'] == 'completed')
    in_progress_count = sum(1 for n in nodes if n['status'] == 'in_progress')
    crashed_count = sum(1 for n in nodes if n['is_crashed'])
    overall_progress = round(sum(n['progress_pct'] for n in nodes) / len(nodes), 1) if nodes else 0.0

    return {
        'enabled': True,
        'project_id': project.id,
        'project_name': project.name,
        'nodes': nodes,
        'edges': edges,
        'summary': {
            'total_phases': len(nodes),
            'completed_phases': completed_count,
            'in_progress_phases': in_progress_count,
            'crashed_phases': crashed_count,
            'overall_progress': overall_progress,
            'failsafe_rerouted': crashed_count > 0
        }
    }
