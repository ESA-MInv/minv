from django.conf.urls import url

from minv.tasks import views

urlpatterns = ([
    url(r'^$', views.job_list_view, name="job-list"),
    url(r'^(?P<job_id>[\w{}.-]+)/$', views.job_view, name="job")
], "tasks", "tasks")
