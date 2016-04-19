import os
import socket
from os.path import dirname, isdir
from signal import SIGTERM, SIGINT, signal
import logging
import errno
from multiprocessing.connection import Listener, Client
from multiprocessing.pool import ThreadPool

from django.conf import settings

from minv.config import DaemonReader
from minv.tasks.scheduler import Scheduler
from minv.tasks import models
from minv.tasks.registry import registry


logger = logging.getLogger(__name__)


class Daemon(object):
    """ Multi-purpose task management daemon.
    """
    def __init__(self):
        self.scheduler = None
        self.listener = None
        self.executor_pool = None

    def run(self):
        try:
            # setup signal handlers for shutdown or immediate termination
            signal(SIGINT, self.shutdown)
            signal(SIGTERM, self.terminate)

            reader = DaemonReader()

            registry.initialize(getattr(settings, 'MINV_TASK_MODULES', []))

            # create executors, listener and scheduler
            self.executor_pool = ThreadPool(reader.num_workers)  # TODO: threading or process pool
            self.scheduler = Scheduler(self.on_scheduled)
            self.listener = get_listener()

            self.reload_schedule()
            self.scheduler.start()

            while True:
                try:
                    conn = self.listener.accept()
                except socket.error as exc:
                    # connection closed
                    if exc.errno in (errno.EINTR, errno.EBADF):
                        logger.info(
                            "Listener interrupted. Exiting main control loop."
                        )
                        break
                    else:
                        raise

                logger.debug("Client connected: %s", conn)
                message = conn.recv()
                logger.debug("Received message: %r", message)

                if message == "reload":
                    self.reload_schedule()

        finally:
            self.shutdown()

    def shutdown(self, signum=None, frame=None, terminate=False):
        """ Shutdown method. When ``terminate`` is ``True``, then the underlying
        pool is terminated. Otherwise, running tasks are finished.
        """
        if self.executor_pool:
            if terminate:
                self.executor_pool.terminate()
            else:
                self.executor_pool.close()

        if self.scheduler:
            self.scheduler.shutdown()
            self.scheduler = None
        if self.listener:
            self.listener.close()
            self.listener = None

    def terminate(self, signum=None, frame=None):
        self.shutdown(terminate=True)

    def on_scheduled(self, scheduled_task):
        task = scheduled_task.task
        arguments = scheduled_task.arguement_values
        scheduled_task.delete()
        self.executor_pool.apply_async(registry.run, [task], arguments)

    def reload_schedule(self):
        """ Reload the scheduled items from the database.
        """
        self.scheduler.reset()
        scheduled_tasks = models.ScheduledTask.objects.all()
        for scheduled_task in scheduled_tasks:
            self.scheduler.schedule(scheduled_task.when, scheduled_task)


def get_socket_config():
    """ Get path to the harvesing socket file. """
    reader = DaemonReader()

    if reader.port is not None:
        return ("localhost", reader.port), "AF_INET"

    socket_filename = reader.socket_filename

    if socket_filename is None:
        raise RuntimeError(
            "Failed to read daemon.socket_file from configuration."
        )
    # make sure the socket directory exists
    if not isdir(dirname(socket_filename)):
        os.makedirs(dirname(socket_filename))
    return socket_filename, "AF_UNIX"


def get_listener():
    """ Get daemon socket listener (server end-point). """
    address, family = get_socket_config()
    listener = Listener(address, family)
    if family == "AF_UNIX":
        os.chmod(address, 0700)
    return listener


def get_client():
    """ Get daemon socket sender (client end-point). """
    return Client(*get_socket_config())
