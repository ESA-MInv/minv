# ------------------------------------------------------------------------------
#
# Project: Master Inventory <http://github.com/ESA-MInv/minv>
# Authors: Fabian Schindler <fabian.schindler@eox.at>
#
# ------------------------------------------------------------------------------
# Copyright (C) 2016 European Space Agency
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies of this Software or works derived from this Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
# ------------------------------------------------------------------------------


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
        try:
            values = self._argument_values
        except AttributeError:
            values = self._argument_values = json.loads(self.arguments)

        return values

    class Meta:
        abstract = True


class ScheduledJob(TaskBase):
    """ Model class for a scheduled job.
    """
    when = models.DateTimeField()
    last_execution = models.DateTimeField(**optional)

    def __str__(self):
        return "%s at %s seconds args=%s" % (
            self.task, self.when.isoformat(), self.arguments
        )


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

    schedule = models.ForeignKey(ScheduledJob, related_name="jobs", **optional)

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
