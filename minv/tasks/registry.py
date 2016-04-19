from minv.tasks.api import monitor
from minv.tasks import models


class Registry(object):
    def __init__(self, ):
        self._tasks = {}

    def register(self, func_or_name):
        """ Decorator to register a function as a task.
        """
        if callable(func_or_name):
            self._tasks[func_or_name.__name__] = func_or_name
            return func_or_name

        else:
            def wrapped(func):
                self._tasks[func_or_name] = func
                return func
            return wrapped

    def run(self, task, **kwargs):
        with monitor(task, **kwargs):
            self._tasks[task](**kwargs)

    def restart(self, job_id):
        job = models.Job.objects.get(id=job_id)
        kwargs = job.get_arguments()
        with monitor(job.task, **kwargs):
            self._tasks[job.task](**kwargs)

    def initialize(self, module_list=None):
        for module_path in module_list:
            # TODO: import module
            pass

registry = Registry()
task = registry.register
