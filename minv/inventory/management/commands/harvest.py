from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

from minv.tasks.harvest import harvest
from minv.inventory import models


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option("-m", "--mission", dest="mission"),
        make_option("-f", "--file-type", dest="file_type"),
        make_option("-u", "--url", dest="urls", default=None,
            action="append", help="The harvesting location to harvest."
        ),
        make_option("-a", "--all", dest="all",
            action="store_true", default=False,
            help="Harvest all locations from the collection."
        ),
    )

    args = '-m MISSION -f FILE TYPE -u <location-url> [ -u <location-url> ... ]'

    help = 'Harvest the whole collection or specific locations of a collection.'

    def handle(self, *args, **options):
        if not options["urls"]:
            raise CommandError("No location URLs specified.")

        mission = options["mission"]
        file_type = options["file_type"]

        collection = models.Collection.objects.get(
            mission=mission, file_type=file_type
        )

        if options.get("all"):
            urls = collection.locations.values_list("url", flat=True)
        else:
            urls = options["urls"]

        if not urls:
            raise CommandError("No URL locations specified.")

        for url in urls:
            try:
                print "Harvesting location %s of collection %s" % (
                    collection, url
                )
                failed_retrieve, failed_ingest = harvest(mission, file_type, url)
                if failed_retrieve or failed_ingest:
                    print(
                        "Harvesting of location %s failed. Failed to "
                        "retrieve: %s. Failed to ingest: %s" % (
                            url,
                            ", ".join(failed_retrieve)
                            if failed_retrieve else "none",
                            ", ".join(failed_ingest)
                            if failed_ingest else "none",
                        )
                    )
                else:
                    print(
                        "Finished harvesting location %s of collection %s." % (
                            url, collection
                        )
                    )
            except Exception as exc:
                raise CommandError(
                    "Failed to harvest location %s. Error was: %s" % (url, exc)
                )
