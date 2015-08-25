from django.conf.urls import patterns, include, url
from django.contrib import admin

from inventory.urls import urls as inventory_urls


print admin.site.urls
print inventory_urls

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'minv.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'', include(inventory_urls))
)
