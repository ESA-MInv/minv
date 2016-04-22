import os
from os.path import join, basename
from optparse import make_option
import tempfile
import shutil
import glob

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from minv.inventory import models
from minv.inventory.ingest import ingest
from minv.utils import safe_makedirs


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option("-m", "--mission", dest="mission"),
        make_option("-f", "--file-type", dest="file_type"),
        make_option("-u", "--url", dest="urls", action="append", default=None)
    )

    args = '-m MISSION -f FILE TYPE'

    help = ('Reload all index files for selected or all locations in the '
            'collection.')

    def handle(self, *args, **options):
        mission = options["mission"]
        file_type = options["file_type"]
        urls = options["urls"]

        if not mission or not file_type:
            raise CommandError("No collection specified.")

        collection = models.Collection.objects.get(
            mission=mission, file_type=file_type
        )

        if urls:
            locations = [
                collection.locations.get(url=url)
                for url in urls
            ]
        else:
            locations = collection.locations.all()

        for location in locations:
            print "Reloading index files of location %s" % location
            try:
                self.handle_location(collection, location)
                print "Successfully reloaded index files in location %s" % (
                    location
                )
            except Exception as exc:
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

        ingested_dir = join(collection.data_dir, "ingested", location.slug)
        pending_dir = join(collection.data_dir, "pending", location.slug)

        safe_makedirs(ingested_dir)
        safe_makedirs(pending_dir)

        try:
            # move all files from ingested dir to pending dir
            for path in glob.iglob(join(ingested_dir, "*")):
                os.rename(path, join(pending_dir, basename(path)))
            # delete all index file records in database
            location.index_files.all().delete()

            # re-ingest all index files in pending
            for path in glob.iglob(join(pending_dir, "*")):
                ingest(
                    collection.mission, collection.file_type, location.url,
                    basename(path)
                )

        except:
            # restore backups
            shutil.rmtree(collection.data_dir)
            shutil.move(join(tmp_dir, "backup"), collection.data_dir)
        finally:
            shutil.rmtree(tmp_dir)
