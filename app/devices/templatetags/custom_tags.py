# devices/templatetags/custom_tags.py
from django import template

register = template.Library()

@register.filter
def get(dictionary, key):
    return dictionary.get(key)