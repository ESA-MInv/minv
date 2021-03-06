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


import os
import socket
from os.path import dirname, isdir, exists
from signal import SIGTERM, SIGINT, signal
import logging
import errno
from multiprocessing.connection import Listener, Client
from multiprocessing.pool import ThreadPool

from minv.config import GlobalReader
from minv.tasks.scheduler import Scheduler
from minv.tasks import models
from minv.tasks.registry import registry, run_task


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

            registry.initialize()

            # create executors, listener and scheduler
            self.executor_pool = ThreadPool(1)
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

                command = None
                try:
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
                except Exception as exc:
                    logger.exception("Daemon command %s failed." % command)

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

        print task, arguments
        self.executor_pool.apply_async(run_task, [task], arguments)

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
