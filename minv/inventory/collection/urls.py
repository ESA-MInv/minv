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
        url(r'^alignment/$', views.alignment_view, name="alignment"),
        url(r'^export/$', views.export_view, name="export"),
        url(r'^import/$', views.import_view, name="import"),
        url(r'^configuration/$', views.configuration_view, name="configuration"),
    ]))
]
