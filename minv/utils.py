import time
import os
import errno

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
