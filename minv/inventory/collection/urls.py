from django.conf.urls import url, include

from minv.inventory.collection import views


urlpatterns = [
    url(r'^$', views.list_view, name="list"),
    url(r'^(?P<mission>[\w{}.-]+)/(?P<file_type>[\w{}.-]+)/', include([
        url(r'^$', views.detail_view, name="detail"),
        url(r'^harvest/$', views.harvest_view, name="harvest"),
        url(r'^search/$', views.search_view, name="search"),
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
