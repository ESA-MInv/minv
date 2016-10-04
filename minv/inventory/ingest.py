import csv
import os
import errno
from os.path import basename, exists, join, dirname
from datetime import datetime
from urlparse import urlparse
import logging
import traceback
from itertools import islice

from django.db import transaction
from django.utils.dateparse import parse_datetime
from django.utils.timezone import utc
from django.contrib.gis.db.models import (
    DateTimeField, CharField, MultiPolygonField, PointField, IntegerField,
    FloatField
)
from django.contrib.gis.geos import MultiPolygon, Polygon, Point

from minv.inventory import models
from minv.geom_utils import fix_footprint, EmptyMultiPolygon
from minv.utils import safe_makedirs


logger = logging.getLogger(__name__)


def parse_index_time(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y%m%d-%H%M%S").replace(tzinfo=utc)


def parse_footprint(value):
    # we must translate from y/x to x/y here
    try:
        rings = fix_footprint(value)[0]
    except EmptyMultiPolygon:
        return None
    for ring in rings:
        ring[:] = [
            (point[1], point[0])
            for point in ring
        ]
    return MultiPolygon(
        Polygon(*rings)
    )


def parse_point(value):
    if not value:
        return None
    return Point([float(v) for v in value.split(" ")])


def parse_integer(value):
    if not value:
        return None
    return int(value)


def parse_float(value):
    if not value:
        return None
    return float(value)


class IngestError(Exception):
    pass


@transaction.atomic
def ingest(mission, file_type, url, index_file_name):
    """ Function to ingest an indexfile into the collection identified by
    ``mission`` and ``file_type``. The indexfile must be located in the
    ``pending`` folder of the collections data directory.
    When ingested correctly, the index
    """

    collection = models.Collection.objects.get(
        mission=mission, file_type=file_type
    )
    location = models.Location.objects.get(url=url, collection=collection)

    # directories for index files
    pending_dir = join(collection.data_dir, "pending", location.slug)
    ingested_dir = join(collection.data_dir, "ingested", location.slug)
    failed_dir = join(collection.data_dir, "failed", location.slug)

    if (basename(index_file_name) != index_file_name and
            dirname(index_file_name) != pending_dir):
        raise IngestError(
            "Only pass the filename within the 'pending' directory, not the "
            "full path"
        )

    for dir_path in (pending_dir, ingested_dir, failed_dir):
        safe_makedirs(dir_path)

    path = join(pending_dir, index_file_name)
    if not exists(path):
        raise IngestError(
            "No such index file in pending directory: %s" % index_file_name
        )

    try:
        # parse index file name info
        s, e, u = basename(index_file_name).partition(".")[0].split("_")
        index_file = models.IndexFile(
            filename=index_file_name, location=location,
            begin_time=parse_index_time(s), end_time=parse_index_time(e),
            update_time=parse_index_time(u)
        )
        index_file.full_clean()
        index_file.save()

        # prepare value "preparators"
        meta = models.Record._meta
        preparations = {
            "filename": lambda v: basename(urlparse(v).path)
        }

        mapping = collection.get_metadata_field_mapping(url).items()

        if not mapping:
            raise IngestError("No metadata mapping configured for %s/%s %s"
                % (mission, file_type, url)
            )

        for target, _ in mapping:
            field = meta.get_field(target)
            if isinstance(field, DateTimeField):
                preparations[target] = parse_datetime  # TODO: necessary?
            elif isinstance(field, CharField) and field.choices:
                preparations[target] = lambda value: value[0].upper() if len(value) else None
            elif isinstance(field, MultiPolygonField):
                preparations[target] = parse_footprint
            elif isinstance(field, PointField):
                preparations[target] = parse_point
            elif isinstance(field, IntegerField):
                preparations[target] = parse_integer
            elif isinstance(field, FloatField):
                preparations[target] = parse_float

        count = 0
        with open(path) as f:
            reader = csv.DictReader(f, delimiter="\t")

            while True:
                records = []

                # iterate the files rows in chunks
                row = None
                chunk = islice(reader, 5000)

                for row in chunk:
                    record = models.Record(
                        index_file=index_file, location=location
                    )
                    for target, source in mapping:
                        try:
                            value = row[source]
                        except KeyError:
                            raise IngestionError(
                                "Index file '%s' has no such field '%s'."
                                % (index_file_name, source)
                            )
                        preparator = preparations.get(target)
                        if preparator:
                            value = preparator(value)

                        setattr(record, target, value)

                    records.append(record)
                    count += 1

                # check if the slice was empty and exit when the last line of the
                # was read.
                if row is None:
                    break
                else:
                    # save the next chunk of models to the DB
                    models.Record.objects.bulk_create(records)
                    logger.debug(
                        "Ingested chunk of %d records. "
                        "Current total %d records" % (len(records), count)
                    )

    except Exception as exc:
        # move file to failed directory
        os.rename(
            join(pending_dir, index_file_name),
            join(failed_dir, index_file_name)
        )
        logger.error(
            "Failed to ingest index file %s for %s (%s). Error was: %s"
            % (index_file_name, collection, location.url, exc)
        )
        logger.debug(traceback.format_exc())
        raise IngestionError(
            "Failed to ingest index file %s for %s (%s). Error was: %s"
            % (index_file_name, collection, location.url, exc)
        )
    else:
        # move file to ingested directory
        os.rename(
            join(pending_dir, index_file_name),
            join(ingested_dir, index_file_name)
        )
        logger.info(
            "Successfully ingested index file %s for %s (%s) with %d records"
            % (index_file_name, collection, location.url, count)
        )

    return count


class IngestionError(Exception):
    pass
