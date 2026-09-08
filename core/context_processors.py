from .models import Project, ExtractedMetric
from services.addon_manager import get_project_addons
from services.multi_industry_engine import get_industry_details, get_all_industries, INDUSTRIES

def get_or_create_default_project(request=None):
    if request:
        project_id = request.session.get('active_project_id') or request.GET.get('project_id')
        if project_id:
            try:
                p = Project.objects.filter(id=int(project_id)).first()
                if p:
                    return p
            except Exception:
                pass
    project = Project.objects.first()
    if not project:
        project = Project.objects.create(
            name="Default Construction Project",
            code="PRJ-DEF-001",
            description="Active construction workspace.",
            total_budget=1000000.0,
            status="active"
        )
    return project

def inject_global_data(request):
    project = get_or_create_default_project(request)
    all_projects = Project.objects.all().order_by('-created_at')
    pending_review_count = 0
    addons = {}
    if project:
        pending_review_count = ExtractedMetric.objects.filter(status='pending').count()
        addons = get_project_addons(project.id)

    # Resolve active industry from session or project sector or default constructflow
    active_industry_key = 'constructflow'
    if request:
        active_industry_key = request.session.get('active_industry')
    if not active_industry_key and project and hasattr(project, 'industry_sector') and project.industry_sector:
        active_industry_key = project.industry_sector
    if not active_industry_key or active_industry_key not in INDUSTRIES:
        active_industry_key = 'constructflow'

    current_industry = get_industry_details(active_industry_key)
    all_industries = get_all_industries()

    return {
        'current_project': project,
        'all_projects': all_projects,
        'pending_review_count': pending_review_count,
        'addons': addons,
        'current_industry': current_industry,
        'all_industries': all_industries,
        'active_industry_key': active_industry_key
    }


