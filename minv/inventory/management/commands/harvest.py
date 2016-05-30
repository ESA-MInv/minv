from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

from minv.commands import CollectionCommand
from minv.tasks.registry import registry


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

    require_group = "minv_g_operators"

    args = (
        'MISSION/FILE-TYPE ( -u <location-url> [ -u <location-url> ... ] | -a )'
    )

    help = (
        'Harvest the whole collection or specific locations of a collection. '
        'Requires membership of group "minv_g_operators".'
    )

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
                print "Harvesting location %s of collection %s" % (
                    collection, url
                )
                failed_retrieve, failed_ingest = registry.run(
                    "harvest",
                    mission=collection.mission,
                    file_type=collection.file_type,
                    url=url
                )
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
                if options.get("traceback"):
                    raise
                raise CommandError(
                    "Failed to harvest location %s. Error was: %s" % (url, exc)
                )
