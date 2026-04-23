from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    if not mapping or key is None:
        return None
    return mapping.get(str(key))
