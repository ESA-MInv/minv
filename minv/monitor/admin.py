from django.contrib import admin
from django.utils.timezone import now

from minv.monitor import models


def duration(task):
    if task.end_time:
        return str(task.end_time - task.start_time)
    else:
        return str(now() - task.start_time)


class JobAdmin(admin.ModelAdmin):
    list_display = ("id", "task", "status", duration)

admin.site.register(models.Job, JobAdmin)
