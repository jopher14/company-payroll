from django import template
import json

register = template.Library()


@register.filter
def get_item(value, key):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception:
            return None
    if isinstance(value, dict):
        return value.get(key)
    return None
