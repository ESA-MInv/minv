# ------------------------------------------------------------------------------
#
# Project: Master Inventory <http://github.com/ESA-MInv/minv>
# Authors: Fabian Schindler <fabian.schindler@eox.at>
#
# ------------------------------------------------------------------------------
# Copyright (C) 2016 European Space Agency
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies of this Software or works derived from this Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
# ------------------------------------------------------------------------------


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
