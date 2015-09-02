from django.conf.urls import url, include
from minv.inventory import views


urlpatterns = ([
    url(r'^$', views.root_view, name="root"),
    url(r'^collections/', include([
        url(r'^$', views.collection_list_view, name="collection-list"),
        url(r'^(?P<mission>[\w{}.-]+)/(?P<file_type>[\w{}.-]+)/', include([
            url(r'^$', views.collection_detail_view, name="collection-detail"),
            url(r'^harvest/$', views.collection_harvest_view,
                name="collection-harvest"),
            url(r'^search/$', views.collection_search_view,
                name="collection-search"),
            url(r'^alignment/$', views.collection_alignment_view,
                name="collection-alignment"),
            url(r'^export/$', views.collection_export_view,
                name="collection-export"),
            url(r'^import/$', views.collection_import_view,
                name="collection-import"),
            url(r'^configuration/$', views.collection_configuration_view,
                name="collection-configuration"),
        ]))
    ])),
    url(r'^monitor/$', views.task_monitor_view, name="task-monitor"),
    url(r'^login/$', views.login_view, name="login"),
    url(r'^logout/$', views.logout_view, name="logout"),
], "inventory", "inventory")
