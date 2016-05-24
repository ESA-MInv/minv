from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

from minv.commands import CollectionCommand
from minv.inventory import models


class Command(CollectionCommand):
    option_list = BaseCommand.option_list + (
        make_option("-u", "--url", dest="urls", default=None,
            action="append", help="The harvesting location to harvest."
        ),
        make_option("-a", "--all", dest="all",
            action="store_true", default=False,
            help="Harvest all locations from the collection."
        ),
    )

    args = (
        'MISSION/FILE-TYPE ( -u <location-url> [ -u <location-url> ... ] | -a )'
    )

    help = 'Clear the harvested data from the specified locations.'

    def handle_collection(self, collection, *args, **options):
        if not options["urls"] and not options["all"]:
            raise CommandError("No location URLs specified.")

        if options.get("all"):
            urls = collection.locations.values_list("url", flat=True)
        else:
            urls = options["urls"]

        if not urls:
            raise CommandError("No URL locations specified.")

        for url in urls:
            try:
                location = collection.locations.get(url=url)
                print "Deleting all content for location %s on collection %s" % (
                    location, collection
                )
                location.index_files.all().delete()
                print(
                    "Finished deleting all content for location %s on "
                    "collection %s" % (
                        location, collection
                    )
                )
                # TODO: delete all files as-well

            except models.Location.DoesNotExist:
                raise CommandError("No such location '%s' on collection %s" % (
                    url, collection
                ))
