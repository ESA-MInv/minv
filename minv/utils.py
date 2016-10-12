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


import time
import os
import errno
import fcntl
from functools import wraps
from datetime import timedelta, datetime
import re

from django.core.exceptions import ObjectDoesNotExist


def get_or_none(qs, *args, **kwargs):
    try:
        return qs.get(*args, **kwargs)
    except ObjectDoesNotExist:
        return None


class Timer(object):
    """ Time interval measuring class. """
    def __init__(self):
        self._start = None
        self._stop = None
        self.start()

    def start(self):
        """ Start (reset) the timer. """
        self._start = time.time()

    def stop(self):
        """ Stop the timer and return the ellapsed time in seconds. """
        self._stop = time.time()
        return self._stop - self._start


def safe_makedirs(path, mode=0770):
    """ Safely create a diretory path, ignoring errors when it already exists.
    """
    try:
        os.makedirs(path, mode)
    except OSError as error:
        # propagate any exception other than the error indicating that the
        # directories already exist
        if error.errno != errno.EEXIST:
            raise


RE_ISO_8601_DURATION = re.compile(
    r"^(?P<sign>[+-])?P"
    r"(?:(?P<years>\d+(\.\d+)?)Y)?"
    r"(?:(?P<months>\d+(\.\d+)?)M)?"
    r"(?:(?P<days>\d+(\.\d+)?)D)?"
    r"T?(?:(?P<hours>\d+(\.\d+)?)H)?"
    r"(?:(?P<minutes>\d+(\.\d+)?)M)?"
    r"(?:(?P<seconds>\d+(\.\d+)?)S)?$"
)


def parse_duration(value):
    """ Parses an ISO 8601 duration string into a python timedelta object.
    Raises a `ValueError` if the conversion was not possible.
    """
    if isinstance(value, timedelta):
        return value

    match = RE_ISO_8601_DURATION.match(value)
    if not match:
        raise ValueError(
            "Could not parse ISO 8601 duration from '%s'." % value
        )
    match = match.groupdict()

    sign = -1 if "-" == match['sign'] else 1
    days = float(match['days'] or 0)
    days += float(match['months'] or 0) * 30  # ?!
    days += float(match['years'] or 0) * 365  # ?!
    fsec = float(match['seconds'] or 0)
    fsec += float(match['minutes'] or 0) * 60
    fsec += float(match['hours'] or 0) * 3600

    return sign * timedelta(days, fsec)


def total_seconds(tdelta):
    """ Calculate the total number of seconds of a timedelta object. Workaround
    for missing method of :class:`datetime.timedelta` objects in Python 2.6.
    """
    return 1e-6*tdelta.microseconds + tdelta.seconds + 8.64e+4*tdelta.days


# adapted from https://gist.github.com/thatalextaylor/7408395

def timedelta_to_duration(tdelta):
    seconds = total_seconds(tdelta)
    sign_string = '-' if seconds < 0 else ''
    seconds = abs(int(seconds))
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    parts = [sign_string, "P"]

    if days > 0:
        parts.append("%sD" % days)

    if hours or minutes or seconds:
        parts.append("T")

        if hours:
            parts.append("%sH" % hours)

        if minutes:
            parts.append("%sM" % minutes)

        if seconds:
            parts.append("%sS" % seconds)

    return "".join(parts)


def timestamp(dt):
    """ Returns a unix timestamp from a given datetime.
    """
    return int(total_seconds(dt - datetime(1970, 1, 1, tzinfo=dt.tzinfo)))


class FileLockException(Exception):
    """ File lock error exception. """
    pass


class FileLock(object):
    """ Generic file-based lock.

        The unix flock(2) advisory file lock is employed by the lock
        object. The flock(2) causes the lock to be automatically released
        upon process termination (including SIGKILL).

        The lock file can exist before acquiring the lock. If not
        existent the file is created.  When possible, the locked file
        is automatically removed at the lock release.

        The existence of the lock file itself does not mean the lock
        is already held by some other process or thread. On the other
        hand, the lock cannot be held without the actual lock file.

        NOTE: Never, ever, remove the lock file unless you are absolutely
        sure the lock is not held by another running process or thread.
        The removal of the lock file causes the lock to be released with all
        possible dangerous consequences while keeping unused lockfiles does
        not cause any harm.
    """

    def __init__(self, lockfile=None):
        self.lockfile = lockfile
        self._fobj = None

    @property
    def is_locked(self):
        """ See if we are currently locking the lock file. """
        return self._fobj is not None

    def acquire(self):
        """ Acquire the file lock or raise FileLockException
        if the lock has been already acquired by someone else.
        """
        if self.is_locked:
            return
        # NOTE: The existence of the lockfile as such does not imply that
        # the file is already locked.
        fobj = open(self.lockfile, "w+")
        try:
            # Acquire an exclusive lock for the open file.
            fcntl.flock(fobj, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError as exc:
            fobj.close()
            if exc.errno == errno.EAGAIN:
                raise FileLockException(
                    "File is locked! FILE=%s" % self.lockfile
                )
            raise
        except:
            fobj.close()
            raise
        else:
            self._fobj = fobj

    def release(self):
        """ Release the file lock. """
        if self.is_locked:
            # NOTE: The file must be unlinked BEFORE the actual unlocking.
            os.unlink(self.lockfile)
            # NOTE: The explicit unlocking is redundant. The file lock
            #       is automatically removed upon file close.
            # fcntl.flock(self._fobj, fcntl.LOCK_UN)
            self._fobj.close()
            self._fobj = None

    def __del__(self):
        """ Make sure the lock is released upon object removal.
        """
        self.release()

    def __enter__(self):
        """ Context guard entry. """
        self.acquire()
        return self

    def __exit__(self, *args):
        """ Context guard exit. """
        self.release()


def file_locked(lockfile):
    """ Decorator to secure a function with a file lock.
    """
    def outer_wrapper(func):
        """ file_locked outer wrapper """
        @wraps(func)
        def wrapper(*args, **kwargs):
            """ file_locked inner wrapper """
            with FileLock(lockfile):
                return func(*args, **kwargs)
        return wrapper
    return outer_wrapper
