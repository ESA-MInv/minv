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
        make_option("-o", "--output", dest="output",
            default=None,
            help="Define the output filename. Mandatory."
        ),
        make_option("--configuration", dest="configuration",
            action="store_true", default=True,
            help="Export the configuration. This is the default."
        ),
        make_option("--no-configuration", dest="configuration",
            action="store_false", default=True,
            help="Do not export the configuration."
        ),
        make_option("--data", dest="data",
            action="store_true", default=True,
            help="Export the data. This is the default."
        ),
        make_option("--no-data", dest="data",
            action="store_false", default=True,
            help="Do not export the data."
        )
    )

    require_group = "minv_g_app_engineers"

    args = 'MISSION/FILE-TYPE [ -o <export-filename> ] ' \
           '[ --configuration | --no-configuration ] ' \
           '[ --data | --no-data ]'

    help = (
        'Export the configuration and/or data of the specified collection. '
        'Requires membership of group "minv_g_app_engineers".'
    )

    def handle_collection(self, collection, *args, **options):
        output = options["output"]
        registry.initialize()

        try:
            filename = registry.run(
                "export",
                mission=collection.mission,
                file_type=collection.file_type,
                filename=output,
                configuration=options["configuration"],
                data=options["data"]
            )
            print "Exported collection %s to %s" % (
                collection, filename
            )
        except Exception as exc:
            raise CommandError(
                "Failed to export collection %s to %s. Error was: %s" % (
                    collection, options["output"], exc
                )
            )
