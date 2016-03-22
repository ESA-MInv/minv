import time

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
