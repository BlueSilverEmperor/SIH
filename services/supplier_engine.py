import math
from core.models import Supplier
from services.addon_manager import is_addon_enabled


def compute_softmax_for_group(suppliers, temperature=10.0):
    if not suppliers:
        return
    scores = [s.calculate_weighted_score() for s in suppliers]
    max_score = max(scores) if scores else 0.0
    scaled_scores = [(sc - max_score) / temperature for sc in scores]
    exp_scores = [math.exp(sc) for sc in scaled_scores]
    sum_exp = sum(exp_scores)

    for i, s in enumerate(suppliers):
        s.softmax_probability = exp_scores[i] / sum_exp if sum_exp > 0 else 1.0 / len(suppliers)
        s.save()


def calculate_supplier_scores_and_softmax(category=None, temperature=10.0, project_id=None):
    """
    Add-On 1: Intelligent Supplier-Rating & Softmax Engine.
    Computes weighted scores and Softmax decision probabilities for suppliers, grouped per category.
    Weighted criteria:
    - TCO/ROI: 30%
    - Delivery Reliability: 25%
    - Quality Score: 20%
    - Financial Stability: 15%
    - ESG/Sustainability: 10%
    """
    # Check if Add-On 1 is enabled
    if project_id and not is_addon_enabled(project_id, 'supplier_softmax_engine'):
        all_suppliers = list(Supplier.objects.all())
        for s in all_suppliers:
            s.calculate_weighted_score()
            s.softmax_probability = 0.0
            s.save()
        return all_suppliers

    if category and category != 'All':
        suppliers = list(Supplier.objects.filter(category=category))
        compute_softmax_for_group(suppliers, temperature=temperature)
        return suppliers

    all_suppliers = list(Supplier.objects.all())
    categories = set(s.category for s in all_suppliers)

    for cat in categories:
        cat_suppliers = [s for s in all_suppliers if s.category == cat]
        compute_softmax_for_group(cat_suppliers, temperature=temperature)

    return all_suppliers


def get_recommended_supplier_by_category(project_id=None):
    """
    Returns top recommended vendor for each procurement category based on highest Softmax probability.
    """
    if project_id and not is_addon_enabled(project_id, 'supplier_softmax_engine'):
        return {
            'enabled': False,
            'message': 'Intelligent Supplier-Rating & Softmax Engine Add-On is disabled.'
        }

    categories = ['Steel Rebar', 'Concrete', 'Masonry', 'Electrical', 'Plumbing', 'General']
    recommendations = {}

    for cat in categories:
        suppliers = calculate_supplier_scores_and_softmax(category=cat, project_id=project_id)
        if suppliers:
            top_supplier = max(suppliers, key=lambda s: s.softmax_probability)
            recommendations[cat] = top_supplier.to_dict()
        else:
            recommendations[cat] = None

    return {
        'enabled': True,
        'recommendations': recommendations
    }
