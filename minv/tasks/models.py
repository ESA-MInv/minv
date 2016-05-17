from uuid import uuid4
import json

from django.db import models
from django.utils.timezone import now


def uuid_default():
    return uuid4().hex


optional = dict(null=True, blank=True)


class TaskBase(models.Model):
    """ Base class for scheduled or running tasks
    """
    task = models.CharField(max_length=256)
    arguments = models.TextField()

    @property
    def argument_values(self):
        return json.loads(self.arguments)

    class Meta:
        abstract = True


class Schedule(TaskBase):
    """ Model class for a scheduled job.
    """
    duration = models.FloatField()
    last_execution = models.DateTimeField(**optional)


class Job(TaskBase):
    """ Model class for a pending, running or somehow finished job.
    """

    id = models.CharField(max_length=32, primary_key=True, default=uuid_default)
    status = models.CharField(max_length=16, choices=(("pending", "Pending"),
                                                      ("running", "Running"),
                                                      ("finished", "Finished"),
                                                      ("failed", "Failed"),
                                                      ("aborted", "Aborted")),
                              default="pending")

    schedule = models.ForeignKey(Schedule, related_name="jobs", **optional)

    error = models.TextField(**optional)
    traceback = models.TextField(**optional)

    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(**optional)

    @property
    def run_time(self):
        if self.end_time:
            return self.end_time - self.start_time
        elif self.status == "running":
            return now() - self.start_time
        return None

    def __str__(self):
        return self.id if self.id else 'Job object'
