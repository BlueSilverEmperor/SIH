import json
from core.models import Project, ProjectAddOn

DEFAULT_ADDONS = {
    'supplier_softmax_engine': {
        'name': 'Intelligent Supplier-Rating & Softmax Engine',
        'description': 'Plug-and-play vendor scoring module that computes TCO, quality, delivery, and Softmax probabilistic allocation for procurement.',
        'icon': 'truck',
        'default': True
    },
    'blender_3d_generator': {
        'name': 'Blender 3D Blueprint Generator',
        'description': 'Optional service module that compiles 2D parsed blueprints into interactive 3D .obj/.glb models via UI trigger button.',
        'icon': 'box',
        'default': True
    },
    'daily_progress_audit': {
        'name': 'Daily Progress Tracker & Audit Service',
        'description': 'Optional daily logging pipeline that audits field progress against planned velocity and flags schedule deviations.',
        'icon': 'clock',
        'default': True
    },
    'early_deadline_failsafe': {
        'name': '3-Day Early Deadline Fail-Safe Re-Organization Engine',
        'description': 'Algorithmic add-on that automatically reorganizes task dependencies and crashes critical path tasks to enforce completion 3 days before deadline.',
        'icon': 'shield-alert',
        'default': True
    },
    'visual_flowchart_workflow': {
        'name': 'Interactive Visual Pipeline & Flowchart Workflow',
        'description': 'Dynamic step-by-step flowchart workflow generator mapping construction phases, real-time node progress, and fail-safe re-routing arrows.',
        'icon': 'sitemap',
        'default': True
    },
    'ar_bim_overlay': {
        'name': 'AR BIM Site Overlay & Spatial Alignment',
        'description': 'WebXR and spatial 3D viewport overlay engine displaying structural CAD/BIM models over live camera feed and site photography.',
        'icon': 'glasses',
        'default': True
    },
    'weather_risk_hedging': {
        'name': 'Weather-Risk Scheduling Hedging Engine',
        'description': 'Automated weather risk analysis module evaluating precipitation & wind hazards on outdoor tasks to inject protective schedule buffer days.',
        'icon': 'cloud-sun-rain',
        'default': True
    },
    'voice_field_logging': {
        'name': 'Voice-Activated Field Logging Engine',
        'description': 'Speech-to-Text field note dictation interface feeding transcribed audio directly into AI structural & labor metric extraction.',
        'icon': 'microphone',
        'default': True
    },
    'geofenced_qr_attendance': {
        'name': 'Geofenced Companion App & Dual QR Attendance',
        'description': 'Standalone mobile extension with GPS perimeter validation and daily-refreshing cryptographic morning check-in and evening check-out QR codes.',
        'icon': 'qrcode',
        'default': True
    },
    'cctv_surveillance_module': {
        'name': 'Real-Time CCTV Surveillance & Monitoring Module',
        'description': 'Live streaming gateway for site-specific IP cameras featuring sub-second HLS/WebRTC streaming, token security, multi-camera grid, and AI visual progress audit.',
        'icon': 'video',
        'default': True
    }
}


def ensure_project_addons_initialized(project_id):
    """
    Guarantees that all registered add-ons have DB records for the given project.
    """
    project = Project.objects.filter(id=project_id).first()
    if not project:
        return {}

    existing = {ao.addon_key: ao for ao in ProjectAddOn.objects.filter(project_id=project_id)}
    
    for key, meta in DEFAULT_ADDONS.items():
        if key not in existing:
            ProjectAddOn.objects.create(
                project=project,
                addon_key=key,
                is_enabled=meta['default']
            )

    return get_project_addons(project_id)


def get_project_addons(project_id):
    """
    Returns a dictionary of add-on keys to boolean enabled states for the project.
    """
    if not project_id:
        # Default all to enabled if no project selected
        return {key: meta['default'] for key, meta in DEFAULT_ADDONS.items()}

    addons_qs = ProjectAddOn.objects.filter(project_id=project_id)
    if not addons_qs.exists():
        return ensure_project_addons_initialized(project_id)

    status_dict = {}
    for ao in addons_qs:
        status_dict[ao.addon_key] = ao.is_enabled

    # Fill any missing keys
    for key, meta in DEFAULT_ADDONS.items():
        if key not in status_dict:
            status_dict[key] = meta['default']

    return status_dict


def get_addon_details(project_id):
    """
    Returns full metadata + current status for all add-ons for UI control panel.
    """
    statuses = get_project_addons(project_id)
    result = []
    for key, meta in DEFAULT_ADDONS.items():
        result.append({
            'key': key,
            'name': meta['name'],
            'description': meta['description'],
            'icon': meta['icon'],
            'is_enabled': statuses.get(key, True)
        })
    return result


def is_addon_enabled(project_id, addon_key):
    """
    Checks if a specific add-on is enabled for the project.
    """
    if not project_id:
        return True
    
    addon = ProjectAddOn.objects.filter(project_id=project_id, addon_key=addon_key).first()
    if addon is not None:
        return addon.is_enabled
    
    # Default fallback
    meta = DEFAULT_ADDONS.get(addon_key)
    return meta['default'] if meta else True


def set_addon_status(project_id, addon_key, is_enabled):
    """
    Enables or disables an add-on for a given project.
    """
    project = Project.objects.filter(id=project_id).first()
    if not project:
        return False, "Project not found"

    addon, created = ProjectAddOn.objects.get_or_create(
        project=project,
        addon_key=addon_key,
        defaults={'is_enabled': is_enabled}
    )
    if not created:
        addon.is_enabled = is_enabled
        addon.save()

    return True, f"Add-on '{addon_key}' set to {'enabled' if is_enabled else 'disabled'}"


def toggle_addon(project_id, addon_key):
    """
    Toggles the current enabled status of an add-on.
    """
    current = is_addon_enabled(project_id, addon_key)
    new_state = not current
    success, msg = set_addon_status(project_id, addon_key, new_state)
    return {
        'success': success,
        'message': msg,
        'addon_key': addon_key,
        'is_enabled': new_state,
        'all_addons': get_project_addons(project_id)
    }
