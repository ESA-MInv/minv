from django.conf.urls import url, include

from minv.inventory.collection.urls import urlpatterns as collection_urlpatterns
from minv.inventory import views


urlpatterns = ([
    url(r'^backup/$', views.backup_view, name="backup"),
    url(r'^restore/$', views.restore_view, name="restore"),
    url(r'^collections/',
        include(collection_urlpatterns, namespace="collection")
    )
], "inventory", "inventory")
