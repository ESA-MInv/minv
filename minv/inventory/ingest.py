import csv
from os.path import basename
from datetime import datetime

from django.db import transaction
from django.utils.dateparse import parse_datetime
from django.utils.timezone import utc
from django.contrib.gis.db.models import DateTimeField, CharField, PolygonField

from minv.inventory import models


def parse_index_time(value):
    return datetime.strptime(value, "%Y%m%d-%H%M%S").replace(tzinfo=utc)


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
    location = models.Location.objects.get(url=url)

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
    preparations = {}

    mapping = collection.get_metadata_field_mapping().items()
    for target, _ in mapping:
        field = meta.get_field(target)
        if isinstance(field, DateTimeField):
            preparations[target] = parse_datetime  # TODO: necessary?
        elif isinstance(field, CharField) and field.choices:
            preparations[target] = lambda value: value[0].upper()
        elif isinstance(field, PolygonField):
            pass # TODO: paprse polygon

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

        return count


class IngestionError(Exception):
    pass
