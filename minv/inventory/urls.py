from django.conf.urls import url, include

from minv.monitor.urls import urlpatterns as monitor_urlpatterns
from minv.inventory.collection.urls import urlpatterns as collection_urlpatterns
from minv.inventory import views


urlpatterns = ([
    url(r'^login/$', views.login_view, name="login"),
    url(r'^logout/$', views.logout_view, name="logout"),
    url(r'^$', views.root_view, name="root"),
    url(r'^backup/$', views.backup_view, name="backup"),
    url(r'^restore/$', views.restore_view, name="restore"),
    url(r'^collections/',
        include(collection_urlpatterns, namespace="collection")
    ),
    url(r'^monitor/', include(monitor_urlpatterns, namespace="monitor"))
], "inventory", "inventory")
