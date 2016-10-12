# ------------------------------------------------------------------------------
#
# Project: Master Inventory <http://github.com/ESA-MInv/minv>
# Authors: Fabian Schindler <fabian.schindler@eox.at>
#
# ------------------------------------------------------------------------------
# Copyright (C) 2016 European Space Agency
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies of this Software or works derived from this Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
# ------------------------------------------------------------------------------


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
