from django import template

register = template.Library()

@register.filter
def until(start, end):
    """
    Custom filter to generate a range from `start` to `end`
    Usage: {% for i in 1|until:5 %} will loop 1, 2, 3, 4
    """
    return range(int(start), int(end))
