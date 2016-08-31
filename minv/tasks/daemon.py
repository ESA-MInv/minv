import os
import socket
from os.path import dirname, isdir, exists
from signal import SIGTERM, SIGINT, signal
import logging
import errno
from multiprocessing.connection import Listener, Client
from multiprocessing.pool import ThreadPool, Pool

from minv.config import GlobalReader
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
        """ Run the Daemon. Setup signal handler, task registry, scheduler,
        listener and executors. Runs the main control loop.
        """
        try:
            # setup signal handlers for shutdown or immediate termination
            signal(SIGINT, self.shutdown)
            signal(SIGTERM, self.terminate)

            reader = GlobalReader()

            registry.initialize()

            # create executors, listener and scheduler
            self.executor_pool = ThreadPool(5)
            self.scheduler = Scheduler(self.on_scheduled)
            self.listener = get_listener()

            self.scheduler.start()
            self.reload_schedule()

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

                command = message[0]
                params = message[1:]

                if command == "reload":
                    self.reload_schedule()

                elif command == "restart":
                    job = models.Job.objects.get(id=params[0])
                    logger.info("Restarting job '%s'" % job)
                    self.executor_pool.apply_async(
                        registry.run, [job], job.arguments
                    )
                elif command == "abort":
                    pass
                    # TODO: implement
                    # job = models.Job.objects.get(id=params[0])
                    # logger.info("Restarting job '%s'" % job)
                    # self.executor_pool.apply_async(
                    #     registry.run, [job], job.arguments
                    # )

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
        arguments = scheduled_task.argument_values
        scheduled_task.delete()
        self.executor_pool.apply_async(registry.run, [task], arguments)

    def reload_schedule(self):
        """ Reload the scheduled items from the database.
        """
        self.scheduler.reset()
        for scheduled_task in models.ScheduledJob.objects.all():
            self.scheduler.schedule(scheduled_task.when, [scheduled_task])


def get_socket_config():
    """ Get path to the harvesing socket file. """
    reader = GlobalReader()

    if reader.daemon_port is not None:
        return ("localhost", reader.daemon_port), "AF_INET"

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
    if family == "AF_UNIX" and exists(address):
        os.unlink(address)

    listener = Listener(address, family)
    if family == "AF_UNIX":
        os.chmod(address, 0700)
    return listener


def get_client():
    """ Get daemon socket sender (client end-point). """
    return Client(*get_socket_config())


def send_reload_schedule():
    """ Send a message to the daemon to reload its schedule.
    """
    client = get_client()
    client.send(("reload",))


def send_restart_job(job_uuid):
    """ Send a message to the daemon to restart a job.
    """
    client = get_client()
    client.send(("restart", job_uuid))


def send_abort_job(job_uuid):
    """ Send a message to the daemon to abort a job.
    """
    client = get_client()
    client.send(("abort", job_uuid))
