from django import template

register = template.Library()

@register.filter
def get(dictionary, key):
    """Safely get a value from a dictionary using a dynamic key in Django templates."""
    return dictionary.get(key, "Key not found")

@register.filter
def at(l, id):
    return l[id]

@register.filter
def to_rgb(tup):
    if tup is None:
        # default rbg is grey
        return  '137, 144, 150'
    return ','.join([str(x) for x in tup])
