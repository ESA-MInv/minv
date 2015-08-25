import csv
from os.path import basename
from datetime import datetime

from django.db.transaction import atomic
from django.utils.dateparse import parse_datetime
from django.utils.timezone import utc
from django.db import models

from inventory.models import Collection, Location, Record, IndexFile
from monitor.tasks import monitor


def parse_index_time(value):
    return datetime.strptime(value, "%Y%m%d-%H%M%S").replace(tzinfo=utc)


@atomic
def ingest(mission, file_type, url, index_file_name):
    # start monitored ingest of file
    with monitor("ingest", mission=mission, file_type=file_type, url=url):
        collection = Collection.objects.get(mission=mission, file_type=file_type)
        location = Location.objects.get(url=url)

        # parse index file name info
        s, e, u = basename(index_file_name).partition(".")[0].split("_")
        print s, e, u
        index_file = IndexFile(
            filename=index_file_name, location=location,
            begin_time=parse_index_time(s), end_time=parse_index_time(e),
            update_time=parse_index_time(u)
        )
        index_file.full_clean()
        index_file.save()

        # prepare value "preparators"
        meta = Record._meta
        preparations = {}

        mapping = collection.get_metadata_field_mapping().items()
        for _, target in mapping:
            field = meta.get_field(target)
            if isinstance(field, models.DateTimeField):
                preparations[target] = parse_datetime  # TODO: necessary?
            elif isinstance(field, models.CharField) and field.choices:
                preparations[target] = lambda value: value[0].upper()

        print mapping

        with open(index_file_name) as f:
            reader = csv.DictReader(f, delimiter="\t")
            print reader
            for row in reader:
                print row
                record = Record(index_file=index_file, location=location)
                for source, target in mapping:
                    value = row[source]
                    preparator = preparations.get(target)
                    if preparator:
                        value = preparator(value)
                    setattr(record, target, value)

                record.full_clean()
                record.save()
