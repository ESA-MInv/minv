from django.template.loader import render_to_string
from django.db import connection
from django.db.models import Min, Count

from minv.inventory import models


def search(collection, filters=None, queryset=None):
    """ Performs a search for :class:`Record`s on the specified
    :class:`Collection` with the given filters applied.

    :param collection: the collection to search on
    :param filters: a dictionary of search parameters

    :returns: the search results
    :rtype: :class:`QuerySet`
    """
    qs = queryset or models.Record.objects.filter(
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
            elif isinstance(value, list):
                if len(value) == 2:
                    low, high = value
                    if key == "acquisition_date":
                        key_low = "begin_date"
                        key_high = "end_date"
                    else:
                        key_low = key
                        key_high = key

                    filter_ = {
                        "%s__lte" % key_low: high, "%s__gte" % key_high: low
                    }
                else:
                    # TODO implement area filtering
                    filter_ = {}

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
        self._qs = models.Record.objects.filter(
            location__in=locations
        ).values("filename").annotate(
            Min("checksum"), Count("annotations")
        )

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
        query = render_to_string("inventory/collection/alignment.sql", {
            "locations": self._locations, "base_query": self._qs.query
        })

        cursor = connection.cursor()
        cursor.execute(query)
        for row in cursor:
            checksums = row[3:]
            yield {
                "filename": row[0], "checksum_mismatch": bool(
                    len(set([c for c in checksums if c is not None]))-1
                ),
                "incidences": checksums, "annotation_count": row[2],
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
        return self._qs.count()

    def __getitem__(self, slc):
        """ Passes the slice to the underlying :class:`QuerySet`.
        """
        if not isinstance(slc, slice):
            raise NotImplementedError("Index access is not supported.")
        self._qs = self._qs[slc]
        return self

    def filter(self, *args, **kwargs):
        """ Passes filters to the underlying :class:`QuerySet`.
        :returns: self
        """
        self._qs = self._qs.filter(*args, **kwargs)
        return self
