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


import logging

from django.utils.importlib import import_module
from django.conf import settings

from minv.tasks.api import monitor
from minv.tasks import models


logger = logging.getLogger(__name__)


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
        name = task if isinstance(task, basestring) else task.task
        with monitor(task, **kwargs):
            return self._tasks[name](**kwargs)

    def restart(self, job_id):
        job = models.Job.objects.get(id=job_id)
        kwargs = job.get_arguments()
        with monitor(job.task, **kwargs):
            return self._tasks[job.task](**kwargs)

    def initialize(self):
        module_list = getattr(settings, 'MINV_TASK_MODULES')

        for module_path in module_list:
            import_module(module_path)

    def get_task_names(self):
        return sorted(self._tasks.keys())

registry = Registry()
task = registry.register


def run_task(task, **kwargs):
    try:
        registry.run(task, **kwargs)
    except Exception as e:
        logger.exception(str(e))
