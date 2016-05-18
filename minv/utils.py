import time
import os
import errno
import fcntl
from functools import wraps

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


def safe_makedirs(path):
    """ Safely create a diretory path, ignoring errors when it already exists.
    """
    try:
        os.makedirs(path)
    except OSError as error:
        # propagate any exception other than the error indicating that the
        # directories already exist
        if error.errno != errno.EEXIST:
            raise


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
