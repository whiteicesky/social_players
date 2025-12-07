from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    try:
        return mapping.get(key)
    except Exception:
        return None


@register.simple_tag
def next_with_anchor(next_url, post_id):
    base = next_url or ''
    if '#' in base:
        base = base.split('#', 1)[0]
    return f'{base}#post-{post_id}'
