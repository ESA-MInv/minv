from django.contrib import admin
from django.utils.timezone import now

from minv.monitor import models


def duration(task):
    if task.end_time:
        return str(task.end_time - task.start_time)
    else:
        return str(now() - task.start_time)


@admin.register(models.Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "status", duration)
