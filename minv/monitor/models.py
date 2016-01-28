from uuid import uuid4
import json

from django.db import models
from django.utils.timezone import now


def uuid_default():
    return uuid4().hex


class Task(models.Model):
    id = models.CharField(max_length=32, primary_key=True, default=uuid_default)
    name = models.CharField(max_length=256)
    arguments = models.TextField()

    status = models.CharField(max_length=16, choices=(("pending", "Pending"),
                                                      ("running", "Running"),
                                                      ("finished", "Finished"),
                                                      ("failed", "Failed"),
                                                      ("aborted", "Aborted")),
                              default="pending")

    error = models.TextField(null=True, blank=True)
    traceback = models.TextField(null=True, blank=True)

    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)

    @property
    def run_time(self):
        if self.end_time:
            return self.end_time - self.start_time
        elif self.status == "running":
            return now() - self.start_time
        return None

    @property
    def argument_values(self):
        return json.loads(self.arguments)
