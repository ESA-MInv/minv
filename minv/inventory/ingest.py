import csv
import os
import errno
from os.path import basename, exists, join
from datetime import datetime
from urlparse import urlparse
import logging

from django.db import transaction
from django.utils.dateparse import parse_datetime
from django.utils.timezone import utc
from django.contrib.gis.db.models import (
    DateTimeField, CharField, MultiPolygonField, PointField
)
from django.contrib.gis.geos import MultiPolygon, Point

from minv.inventory import models
from minv.geom_utils import fix_footprint


logger = logging.getLogger(__name__)


def parse_index_time(value):
    return datetime.strptime(value, "%Y%m%d-%H%M%S").replace(tzinfo=utc)


def parse_footprint(value):
    return MultiPolygon(fix_footprint(value)[0])


def parse_point(value):
    return Point(float(v) for v in value.split(" "))


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

    for dir_path in (pending_dir, ingested_dir, failed_dir):
        try:
            os.makedirs(dir_path)
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise

    if not exists(join(pending_dir, index_file_name)):
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

        mapping = collection.get_metadata_field_mapping().items()
        for target, _ in mapping:
            field = meta.get_field(target)
            if isinstance(field, DateTimeField):
                preparations[target] = parse_datetime  # TODO: necessary?
            elif isinstance(field, CharField) and field.choices:
                preparations[target] = lambda value: value[0].upper()
            elif isinstance(field, MultiPolygonField):
                preparations[target] = parse_footprint
            elif isinstance(field, PointField):
                preparations[target] = parse_point

        count = 0
        with open(index_file_name) as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                # TODO: only insert rows that fit the collection
                record = models.Record(index_file=index_file, location=location)
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

                record.full_clean()
                record.save()
                count += 1
    except:
        # move file to failed directory
        os.rename(
            join(pending_dir, index_file_name),
            join(failed_dir, index_file_name)
        )
        logger.error(
            "Failed to ingest index file %s for %s (%s)"
            % (index_file_name, collection, location.url)
        )
        raise
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
