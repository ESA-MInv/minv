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
from minv.inventory.ingest import ingest


class Command(CollectionCommand):
    option_list = BaseCommand.option_list + (
        make_option("-u", "--url", dest="url",
            help="The associated harvesting location."
        ),
    )

    require_group = "minv_g_operators"

    args = 'MISSION/FILE-TYPE -u URL <index-file-name> ' \
           '[<index-file-name> ...]'

    help = (
        'Ingest the given index files. '
        'Requires membership of group "minv_g_operators".'
    )

    def handle_collection(self, collection, *args, **options):
        for index_file_name in args:
            try:
                # TODO: print number of records ingested
                ingest(
                    collection.mission, collection.file_type, options["url"],
                    index_file_name
                )
            except Exception as exc:
                raise CommandError(
                    "Failed to ingest index file '%s'. Error was: %s"
                    % (index_file_name, exc)
                )
