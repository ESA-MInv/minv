from django.conf.urls import url, include, patterns

from minv import views
from minv.tasks.urls import urlpatterns as tasks_urlpatterns
from minv.inventory.urls import urlpatterns as inventory_urlpatterns


urlpatterns = [
    url(r'^login/$', views.login_view, name="login"),
    url(r'^logout/$', views.logout_view, name="logout"),
    url(r'^$', views.root_view, name="root"),
    url(r'^inventory/', include(inventory_urlpatterns)),
    url(r'^tasks/', include(tasks_urlpatterns))
]
