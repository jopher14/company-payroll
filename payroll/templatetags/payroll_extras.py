from django import template

register = template.Library()


@register.filter
def sum_field(queryset, field):
    """Sums up the given numeric field in a queryset or list of objects."""
    return sum(getattr(item, field, 0) or 0 for item in queryset)
