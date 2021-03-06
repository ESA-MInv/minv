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


from json import dumps
import traceback
import json
from datetime import datetime
import logging

from django.utils.timezone import now

from minv.tasks import models


logger = logging.getLogger(__name__)


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError("Type not serializable")


def monitor(task_or_job, **kwargs):
    """ Context manager wrapper.
    """
    if isinstance(task_or_job, basestring):
        job = models.Job.objects.create(
            task=task_or_job, arguments=dumps(
                kwargs, indent=2, default=json_serial
            )
        )
    else:
        job = task_or_job

    return JobContext(job)


class JobContext(object):
    """ Context manager.
    """
    def __init__(self, job):
        self.job = job

    def __enter__(self):
        self.job.status = "running"
        self.job.start_time = now()
        self.job.full_clean()
        self.job.save()
        logger.info("Starting job %s of task %s." % (self.job, self.job.task))
        return self

    def __exit__(self, etype=None, value=None, tb=None):
        self.job.end_time = now()

        if (etype, value, tb) == (None, None, None):
            self.job.status = "finished"
            logger.info(
                "Job %s of task %s finished after %s." % (
                    self.job, self.job.task, self.job.run_time
                )
            )
        else:
            self.job.status = "failed"
            self.job.error = str(value)
            self.job.traceback = "\n".join(traceback.format_tb(tb))
            logger.error("Job %s of task %s failed after %s." % (
                    self.job, self.job.task, self.job.run_time
                )
            )

        self.job.full_clean()
        self.job.save()


def schedule(task, when, arguments):
    """ Utility function to create a ScheduledJob object, and send a notification
    to the daemon to reload the schedule
    """

    models.ScheduledJob.objects.create(
        task=task, when=when, arguments=json.dumps(arguments)
    )
    send_reload_schedule()


def schedule_many(many):
    """ Utility function to create many ScheduledJob objects, and send a
    notification to the daemon to reload the schedule
    """
    for task, when, arguments in many:
        models.ScheduledJob.objects.create(
            task=task, when=when, arguments=json.dumps(arguments)
        )
    send_reload_schedule()


def send_reload_schedule():
    # import here to resolve circular import issue
    from minv.tasks import daemon
    daemon.send_reload_schedule()


def restart_job(job_or_uuid):
    """ Utility function to restart a job and send a notification to the daemon
    to re-process it.
    """
    if isinstance(job_or_uuid, str):
        job = models.Job.objects.get(id=job_or_uuid)
    else:
        job = job_or_uuid

    job.status = "pending"
    job.full_clean()
    job.save()

    from minv.tasks.daemon import send_restart_job
    send_restart_job(job.id)
