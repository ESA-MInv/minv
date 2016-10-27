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


from datetime import datetime, timedelta

from django.template.loader import render_to_string
from django.db import connection
from django.db.models import Min, Count
from django.contrib.gis.geos import Polygon

from minv.inventory import models


def search(collection, filters=None, queryset=None, area_is_footprint=True):
    """ Performs a search for :class:`Record`s on the specified
    :class:`Collection` with the given filters applied.

    :param collection: the collection to search on
    :param filters: a dictionary of search parameters

    :returns: the search results
    :rtype: :class:`QuerySet`
    """

    if queryset is not None:
        qs = queryset
    else:
        models.Record.objects.filter(
            location__collection=collection
        )

    if filters:
        for key, value in filters.items():

            if value is None or value == "":
                continue

            if key == "locations":
                if not value:
                    continue
                filter_ = {"location__in": value}

            elif isinstance(value, datetime):
                low = value
                high = low + timedelta(days=1)
                if key == "acquisition_date":
                    if key == "acquisition_date":
                        key_low = "begin_time"
                        key_high = "end_time"
                    else:
                        key_low = key
                        key_high = key

                filter_ = {
                    "%s__lt" % key_low: high, "%s__gte" % key_high: low
                }

            elif isinstance(value, list):
                if len(value) == 2:
                    low, high = value
                    if key == "acquisition_date":
                        key_low = "begin_time"
                        key_high = "end_time"
                    else:
                        key_low = key
                        key_high = key

                    filter_ = {
                        "%s__lte" % key_low: high, "%s__gte" % key_high: low
                    }
                elif len(value) == 4:
                    if area_is_footprint:
                        filter_ = {
                            "footprint__intersects": Polygon.from_bbox(value)
                        }
                    else:
                        filter_ = {
                            "scene_centre__within": Polygon.from_bbox(value)
                        }
                else:
                    raise ValueError("Invalid parameter %s: %r" % (key, value))

            elif isinstance(value, basestring):
                if "*" in value:
                    start, _, end = value.partition("*")
                    filter_ = {}

                    if start:
                        filter_["%s__startswith" % key] = start
                    if end:
                        filter_["%s__endswith" % key] = end
                else:
                    filter_ = {key: value}

            else:
                filter_ = {key: value}

            qs = qs.filter(**filter_)

    return qs


def alignment(collection, filters=None):
    """ This function performs the alignment check on the specified
    :class:`Collection` with the given filters applied.

    :returns: the alignment checking results
    :rtype: :class:`AlignmentQuerySet`
    """
    filter_locations = filters.pop("locations", None) if filters else None

    locations_qs = collection.locations.order_by("pk")
    if filter_locations:
        locations_qs = locations_qs.filter(pk__in=filter_locations)
    locations = list(locations_qs)

    qs = AlignmentQuerySet(locations)
    qs = search(collection, filters, qs)

    return locations, qs


class AlignmentQuerySet(object):
    """ Result set for alignment checking.

    The :class:`AlignmentQuerySet` is an object that mimicks Django's
    :class:`QuerySet` but only implements some of the necessary functions.
    """
    def __init__(self, locations):
        self._locations = locations
        self._filters = []
        self._length = None
        self._slice = None

    def _make_query(self, count=False):
        qs = models.Record.objects.filter(
            location__in=self.locations
        ).values("filename").annotate(
            Min("checksum"), Count("annotations")
        )

        for args, kwargs in self._filters:
            qs = qs.filter(*args, **kwargs)

        limit = None
        offset = None
        if not count and self._slice:
            limit = self._slice.stop - self._slice.start
            offset = self._slice.start if self._slice.start > 0 else None

        base_query, params = qs._as_sql(connection)
        query = render_to_string("inventory/collection/alignment.sql", {
            "locations": self._locations, "base_query": base_query,
            "count": count, "limit": limit, "offset": offset
        })

        return query, params

    def __iter__(self):
        """ Executes the underlying query. Yields a :class:`dict` for each
        returned row having the following keys:
            * ``filename``: the current filename
            * ``incidences``: the incidences of the filenames across all
              locations. A :class:`list` containing the checksum for each
              location or ``None`` if the location does not have a record with
              that filename.
            * ``annotation_count``: the number of annotations for the records of
              that filename.
            * ``annotations``: a :class:`QuerySet` with the actual annotations

        """
        query, params = self._make_query()

        location_count = len(self._locations)

        cursor = connection.cursor()
        cursor.execute(query, params)
        for row in cursor:
            checksums = row[3:3+location_count]
            yield {
                "filename": row[0],
                "checksum_mismatch": bool(
                    len(set([c for c in checksums if c is not None]))-1
                ),
                "incidences": zip(checksums, row[3+location_count:]),
                "annotation_count": row[2],
                "annotations": models.Annotation.objects.filter(
                    record__filename=row[0], record__location__in=self._locations
                ).values_list("text", flat=True)
                if row[2] else models.Annotation.objects.none()
            }

    @property
    def locations(self):
        """ Returns the locations this :class:`AlignmentQuerySet` is associated
        with.
        """
        return self._locations

    def __len__(self):
        """ Returns the size of the underlying :class:`QuerySet`.
        """
        if self._length is None:
            query, params = self._make_query(True)
            cursor = connection.cursor()
            cursor.execute(query, params)
            self._length = cursor.fetchone()[0]
        return self._length

    def __getitem__(self, slc):
        """ Passes the slice to the underlying :class:`QuerySet`.
        """
        if not isinstance(slc, slice):
            raise NotImplementedError("Index access is not supported.")
        self._slice = slc
        return self

    def filter(self, *args, **kwargs):
        """ Passes filters to the underlying :class:`QuerySet`.
        :returns: self
        """
        self._filters.append((args, kwargs))
        # self._qs = self._qs.filter(*args, **kwargs)
        return self
