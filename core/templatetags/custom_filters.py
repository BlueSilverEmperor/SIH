import json
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter(name='currency')
def currency(value, decimals=2):
    try:
        val = float(value)
        if int(decimals) == 0:
            return f"{val:,.0f}"
        return f"{val:,.2f}"
    except (ValueError, TypeError):
        return value or "0"

@register.filter(name='abs_val')
def abs_val(value):
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return value

@register.filter(name='pct_int')
def pct_int(value):
    try:
        return int(float(value) * 100)
    except (ValueError, TypeError):
        return 0

@register.filter(name='tojson')
def tojson_filter(value):
    return mark_safe(json.dumps(value))

@register.filter(name='calc_concrete_volume')
def calc_concrete_volume(blueprint):
    if not blueprint:
        return 442.0
    try:
        slab = float(getattr(blueprint, 'slab_area_sqm', 500.0) or 500.0)
        walls = float(getattr(blueprint, 'wall_count', 16) or 16)
        return round(slab * 0.5 + walls * 12.0, 1)
    except Exception:
        return 442.0
