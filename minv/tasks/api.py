from json import dumps
import traceback

from django.utils.timezone import now

from minv.tasks import models


def monitor(task_or_job, **kwargs):
    """ Context manager wrapper.
    """
    if isinstance(task_or_job, basestring):
        job = models.Job.objects.create(
            task=task_or_job, arguments=dumps(kwargs, indent=2)
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
        return self

    def __exit__(self, etype=None, value=None, tb=None):
        if (etype, value, tb) == (None, None, None):
            self.job.status = "finished"
        else:
            self.job.status = "failed"
            self.job.error = str(value)
            self.job.traceback = "\n".join(traceback.format_tb(tb))

        self.job.end_time = now()
        self.job.full_clean()
        self.job.save()
