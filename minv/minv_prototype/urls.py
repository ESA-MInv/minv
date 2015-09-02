from django.conf.urls import patterns, include, url
from django.contrib import admin

from minv.inventory.urls import urlpatterns as inventory_urlpatterns


urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^', include(inventory_urlpatterns)),
    url(r'^', include('django.contrib.auth.urls')),
)
