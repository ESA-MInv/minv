from json import dumps

from django.utils.timezone import now

from minv.monitor import models


def monitor(task, **kwargs):
    """ Context manager wrapper.
    """
    job = models.Job.objects.create(
        task=task, arguments=dumps(kwargs, indent=2)
    )

    return JobContext(job)


class JobContext(object):
    """ Context manager.
    """
    def __init__(self, job):
        self.job = job

    def __enter__(self):
        self.job.start_time = now()
        self.job.full_clean()
        self.job.save()
        return self

    def __exit__(self, etype=None, value=None, traceback=None):
        if (etype, value, traceback) == (None, None, None):
            self.job.status = "finished"
        else:
            self.job.status = "failed"
            self.job.error = str(value)

        self.job.end_time = now()
        self.job.full_clean()
        self.job.save()
