# workouts/templatetags/workout_filters.py
from django import template

register = template.Library()

@register.filter(name='replace')
def replace(value, arg):
    """
    Replaces a substring with another.
    Usage: {{ some_string|replace:"old,new" }}
    """
    if len(arg.split(',')) != 2:
        return value

    old, new = arg.split(',')
    return value.replace(old, new)