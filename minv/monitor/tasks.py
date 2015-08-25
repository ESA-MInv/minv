from json import dumps

from django.utils.timezone import now

from monitor import models


def monitor(name, **kwargs):
    task = models.Task.objects.create(
        name=name, arguments=dumps(kwargs, indent=2))

    return TaskContext(task)


class TaskContext(object):
    def __init__(self, task):
        self.task = task

    def __enter__(self):
        self.task.start_time = now()
        self.task.full_clean()
        self.task.save()
        return self

    def __exit__(self, etype=None, value=None, traceback=None):
        if (etype, value, traceback) == (None, None, None):
            self.task.status = "finished"
        else:
            self.task.status = "failed"
            self.task.error = str(value)

        self.task.end_time = now()
        self.task.full_clean()
        self.task.save()
