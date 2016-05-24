#-------------------------------------------------------------------------------
#
#  SxCat - hervester - task scheduler
#
# Project:  OADS-SxCat
# Authors:  Fabian Schindler <fabian.schindler@eox.at>
#           Martin Paces <martin.paces@eox.at>
#
#-------------------------------------------------------------------------------
# Copyright (C) 2015 European Space Agency

from bisect import insort_left
import pickle
from threading import Thread, Lock, Condition
from datetime import datetime, timedelta
from functools import wraps
import logging
import traceback

from django.utils.timezone import utc


logger = logging.getLogger(__name__)


def how_much_left(value, now=None):
    """ The UTC naive `datetime` value to a `timedelta` indicating amount
    of time to reach the future event. If the event passed already zero
    time-delta is returned:
    """
    ZERO = timedelta(0)
    delta = value - (now or datetime.utcnow())
    return delta if delta > ZERO else ZERO


def total_seconds(tdelta):
    """ Calculate the total number of seconds of a timedelta object. Workaround
    for missing method of :class:`datetime.timedelta` objects in Python 2.6.
    """
    return 1e-6*tdelta.microseconds + tdelta.seconds + 8.64e+4*tdelta.days


def locked(func):
    """ Decorator for proper thread-locking
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        with self._lock:
            return func(self, *args, **kwargs)
    return wrapper


class Scheduler(Thread):
    """ Simple task scheduler. """

    def __init__(self, callback, default_waiting_time=3600.):
        super(Scheduler, self).__init__()
        self._callback = callback
        self._items = []
        self._finished = False
        self._lock = Lock()
        self._cond = Condition(self._lock)
        self._default_waiting_time = default_waiting_time

    @locked
    def load_env(self, filename):
        """ Load scheduled items from a file. """
        with open(filename) as fin:
            self._items = pickle.load(fin)
            self._cond.notify()

    @locked
    def save_env(self, filename):
        """ Save scheduled items to a file. """
        with open(filename, "wb") as fout:
            pickle.dump(self._items, fout)

    @locked
    def shutdown(self):
        """ Shutdown the main thread routine. This *should* terminate the main
        routine almost immediately (with the exception of the case when there
        are currently callbacks running).
        """
        self._finished = True
        self._cond.notify()

    @staticmethod
    def translate_time(when):
        """ Helper to translate timedeltas or timestamps to datetime objects
        """
        if when is None:
            return datetime.utcnow()
        elif isinstance(when, timedelta):
            return when + datetime.utcnow()
        elif isinstance(when, datetime):
            return when.astimezone(utc).replace(tzinfo=None)
        elif isinstance(when, int):
            return datetime.utcfromtimestamp(when)
        else:
            raise ValueError("Invalid scheduled time specification %r!" % when)

    @locked
    def schedule(self, when, args=None, kwargs=None):
        """ Schedule an item. The `when` parameter (either a
        :class:`datetime.datetime`, a :class:`datetime.timedelta` or int)
        defines the scheduled time of execution. The `args`/`kwargs` are for
        arbitrary use and supplied to any callbacks or query functions.
        Set `when` to None to schedule the task for an immediate execution.
        """
        when = self.translate_time(when)
        logger.debug(
            "Scheduling item in %s with args %s and kwargs %s",
            how_much_left(when), args, kwargs
        )
        # time ordering parameter - negative time-delta for descending ordering
        insort_left(self._items, (when, args or (), kwargs or {}))
        self._cond.notify()

    @locked
    def find(self, cond, until=None):
        """ Find the item that satisfies a condition that executes earliest. The
        condition must be a callable that is supplied the arguments and keyword
        arguments as its two parameters.
        Use the `until` parameter to restrict the searched time interval. If
        the `until` parameter is not provided or set to None then all scheduled
        tasks are searched through.
        Returns a 3-tuple: (time of scheduled execution, arguments and
        key-word arguments)
        """
        if until is not None:
            until = self.translate_time(until)

        for when, args, kwargs in self._items:
            # break loop when upper bound is reached
            if until is not None and until < when:
                break

            if cond(args, kwargs):
                logger.debug(
                    "Found matching item scheduled at %s with args %s and "
                    "kwargs %s", when, args, kwargs
                )
                return when, args, kwargs

        return None

    @locked
    def remove(self, cond):
        """ Remove any item from the scheduler that evaluates the given
        condition to true.
        The number of removed items is returned.
        """
        old_count = len(self._items)
        self._items = [
            (when, args, kwargs) for when, args, kwargs in self._items
            if not cond(args, kwargs)
        ]
        new_count = len(self._items)
        logger.debug("Removed %d items from schedule.", old_count - new_count)
        return old_count - new_count

    @locked
    def reset(self):
        """ Remove all items from the scheduler. """
        self._items = []
        self._cond.notify()
        logger.debug("Reset the items in the scheduler.")

    @locked
    def __iter__(self):
        """ Non-blocking iteration over a snapshot of the scheduled items. """
        # copy the list items to allow an early lock release
        items = list(self._items)
        # return a lazy evaluated iterator
        return ((when, args, kwargs) for when, args, kwargs in items)

    @locked
    def run(self):
        """ The main routine of the thread. It periodically checks if one or
        more items are scheduled for execution.
        To save resources, this routine sleeps until the next item is scheduled
        or is woken up if an item was added.
        This routine can be stopped via the :meth:`shutdown` method.
        """
        seconds_to_wait = 0.0
        logger.debug("Scheduler is started.")

        while not self._finished:

            logger.debug("Scheduler will sleep for %f sec.", seconds_to_wait)

            # Wait until schedule change notification or time-out while
            # releasing the undelaying lock.
            # The lock is reacquired again upon the wait finish.
            self._cond.wait(seconds_to_wait)
            logger.debug("Scheduler woke up.")

            # Iterate over the scheduled items and trigger the callback
            # for each that is scheduled for execution.
            # The items are always sorted and we can safely stop the iteration
            # after the first not yet scheduled item.
            # Assuming the schedule items may change while executing
            # the callback.
            while self._items:
                when, args, kwargs = self._items[0]
                if when > datetime.utcnow():
                    break
                # pop the scheduled item
                self._items.pop(0)
                # execute the registered callback
                logger.debug(
                    "Scheduled task is delayed by %f sec.",
                    total_seconds(datetime.utcnow() - when)
                )
                # temporarily release the lock while executing the callback.
                self._lock.release()
                try:
                    self._callback(*args, **kwargs)
                except Exception as e:
                    logger.error(
                        "Error invoking the scheduler callback. Error was %s."
                        % e
                    )
                    logger.debug(traceback.format_exc())
                    raise
                self._lock.acquire()

            # calculate the waiting time for the next
            if self._items:
                seconds_to_wait = max(0.0, total_seconds(
                    self._items[0][0] - datetime.utcnow()
                ))
            else:
                seconds_to_wait = self._default_waiting_time

        logger.debug("Scheduler has stopped.")
