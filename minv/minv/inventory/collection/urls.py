from django.conf.urls import url, include

from minv.inventory.collection import views


urlpatterns = [
    url(r'^$', views.list_view, name="collection-list"),
    url(r'^(?P<mission>[\w{}.-]+)/(?P<file_type>[\w{}.-]+)/', include([
        url(r'^$', views.detail_view, name="collection-detail"),
        url(r'^harvest/$', views.harvest_view,
            name="collection-harvest"),
        url(r'^search/$', views.search_view,
            name="collection-search"),
        url(r'^alignment/$', views.alignment_view,
            name="collection-alignment"),
        url(r'^export/$', views.export_view,
            name="collection-export"),
        url(r'^import/$', views.import_view,
            name="collection-import"),
        url(r'^configuration/$', views.configuration_view,
            name="collection-configuration"),
    ]))
]
