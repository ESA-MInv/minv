from itertools import izip_longest

from django import template


register = template.Library()


def pairwise(iterable):
    """s -> (s0,s1), (s2,s3), (s4, s5), ..."""
    a = iter(iterable)
    return izip_longest(a, a)


@register.inclusion_tag("inventory/extra/form.html")
def render_form(form):
    return {"form": form}
