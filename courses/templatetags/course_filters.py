# courses/templatetags/course_filters.py
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get item from dictionary"""
    if dictionary is None:
        return 0
    return dictionary.get(int(key), 0)