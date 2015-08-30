from django.conf.urls import url
from inventory import views


urls = ([
    url(r'^$', views.collection_list, name="collection-list"),
    url(r'^(?P<mission>[\w{}.-]+)/(?P<file_type>[\w{}.-]+)/$',
        views.collection_detail, name="collection-detail"),
    url(r'^(?P<mission>[\w{}.-]+)/(?P<file_type>[\w{}.-]+)/harvest/$',
        views.collection_harvest, name="collection-harvest"),
    url(r'^(?P<mission>[\w{}.-]+)/(?P<file_type>[\w{}.-]+)/search/$',
        views.collection_search, name="collection-search"),
    url(r'^(?P<mission>[\w{}.-]+)/(?P<file_type>[\w{}.-]+)/alignment/$',
        views.collection_alignment, name="collection-alignment"),
    url(r'^(?P<mission>[\w{}.-]+)/(?P<file_type>[\w{}.-]+)/export/$',
        views.collection_export, name="collection-export"),
    url(r'^(?P<mission>[\w{}.-]+)/(?P<file_type>[\w{}.-]+)/import/$',
        views.collection_import, name="collection-import"),
    url(r'^monitor/$', views.task_monitor, name="task-monitor"),
], "inventory", "inventory")
