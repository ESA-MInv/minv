from itertools import izip_longest

from django import template


register = template.Library()


@register.assignment_tag
def pairwise(iterable):
    """s -> (s0,s1), (s2,s3), (s4, s5), ..."""
    a = iter(iterable)
    return izip_longest(a, a)


@register.inclusion_tag("inventory/extra/form.html")
def render_form(form):
    """ Inclusion tag to render a given form using the default form template.
    """
    return {"form": form}


@register.inclusion_tag("inventory/extra/pagination.html")
def render_pagination(page):
    """ Inclusion tag to render a given paginator.
    """
    return {"page": page}


@register.filter
def get(obj, key):
    """ Filter to get the value of ``obj`` for ``key``.
    """
    try:
        return obj[key]
    except TypeError:
        return getattr(obj, key)


@register.filter
def get_display(obj, key):
    """ Filter to get the display value for field ``key`` of ``obj``.
    """
    try:
        return getattr(obj, "get_%s_display" % key)()
    except AttributeError:
        return get(obj, key)


@register.filter
def sizeof_fmt(num, suffix='B'):
    num = num or 0
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)
