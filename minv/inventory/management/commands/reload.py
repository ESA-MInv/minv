import os
from os.path import join, basename
from optparse import make_option
import tempfile
import shutil
import glob
import csv

from django.core.management.base import BaseCommand
from django.db import transaction

from minv.commands import CollectionCommand
from minv.inventory import models
from minv.inventory.ingest import ingest
from minv.utils import safe_makedirs


class Command(CollectionCommand):
    option_list = BaseCommand.option_list + (
        make_option("-u", "--url", dest="urls", action="append", default=None),
    )

    require_group = "minv_g_operators"

    args = 'MISSION/FILE-TYPE [ -u LOCATION URL [ -u ... ] ]'

    help = (
        'Reload all index files for selected or all locations in the '
        'collection. Requires membership of group "minv_g_operators".'
    )

    def handle_collection(self, collection, *args, **options):
        urls = options["urls"]

        if urls:
            locations = [
                collection.locations.get(url=url)
                for url in urls
            ]
        else:
            locations = list(collection.locations.all())

        for location in locations:
            print "Reloading index files of location %s" % location
            try:
                self.handle_location(collection, location)
                print "Successfully reloaded index files in location %s" % (
                    location
                )
            except Exception as exc:
                if options.get("traceback"):
                    raise
                print (
                    "Failed to reload index files in location %s. "
                    "Error was %s" % (
                        location, exc
                    )
                )

    @transaction.atomic
    def handle_location(self, collection, location):
        tmp_dir = tempfile.mkdtemp()
        shutil.copytree(collection.data_dir, join(tmp_dir, "backup"))
        annotations_file = tempfile.TemporaryFile()

        ingested_dir = join(collection.data_dir, "ingested", location.slug)
        pending_dir = join(collection.data_dir, "pending", location.slug)

        safe_makedirs(ingested_dir)
        safe_makedirs(pending_dir)

        try:
            # move all files from ingested dir to pending dir
            for path in glob.iglob(join(ingested_dir, "*")):
                os.rename(path, join(pending_dir, basename(path)))

            # save all annotations to a CSV
            writer = csv.writer(annotations_file, delimiter="\t")
            writer.writerow(["filename", "annotation"])

            for record in location.records.filter():
                for annotation in record.annotations.all():
                    writer.writerow([record.filename, annotation.text])

            annotations_file.seek(0)

            # delete all index file records in database
            location.index_files.all().delete()

            # re-ingest all index files in pending
            for path in glob.iglob(join(pending_dir, "*")):
                ingest(
                    collection.mission, collection.file_type, location.url,
                    basename(path)
                )

            # restore annotations and remove temporary file
            reader = csv.reader(annotations_file, delimiter="\t")
            next(reader)  # skip header
            for row in reader:
                models.Annotation.objects.create(
                    record=location.records.get(filename=row[0]),
                    text=row[1]
                )

        except:
            # restore backups
            shutil.rmtree(collection.data_dir)
            shutil.move(join(tmp_dir, "backup"), collection.data_dir)
            raise
        finally:
            shutil.rmtree(tmp_dir)
