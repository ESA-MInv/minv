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


from django.conf.urls import url, include

from minv.inventory.collection import views


urlpatterns = [
    url(r'^$', views.list_view, name="list"),
    url(r'^(?P<mission>[\w{}.-]+)/(?P<file_type>[\w{}.-]+)/', include([
        url(r'^$', views.detail_view, name="detail"),
        url(r'^harvest/$', views.harvest_view, name="harvest"),
        url(r'^search/$', views.search_view, name="search"),
        url(r'^search/result-list/$',
            views.result_list_view, name="result_list"
        ),
        url(r'^records/(?P<filename>[\w{}.-]+)$',
            views.record_view, name="record"
        ),
        url(r'^records/(?P<filename>[\w{}.-]+)/annotations/add/$',
            views.annotation_add_view, name="annotation_add"
        ),
        url(r'^records/(?P<filename>[\w{}.-]+)/annotations/delete/$',
            views.annotation_delete_view, name="annotation_delete"
        ),
        url(r'^alignment/$', views.alignment_view, name="alignment"),
        url(r'^export/$', views.export_view, name="export"),
        url(r'^import/$', views.import_view, name="import"),
        url(r'^exports/(?P<filename>[\w{}.-]+)$',
            views.download_export_view, name="exports"
        ),
        url(r'^configuration/$', views.configuration_view, name="configuration"),
    ]))
]
