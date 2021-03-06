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
from django.db import transaction
from django.db.utils import IntegrityError

from minv.commands import MinvCommand
from minv.inventory import models


class Command(MinvCommand):
    option_list = BaseCommand.option_list + (
        make_option("-c", "--create",
            action="store_const", dest="mode", const="create", default="create",
            help="Set the mode to 'create' (the default)."
        ),
        make_option("-d", "--delete",
            action="store_const", dest="mode", const="delete",
            help="Set the mode to 'delete'."
        ),
        make_option("-l", "--list",
            action="store_const", dest="mode", const="list",
            help="Set the mode to 'list'."
        ),
        make_option("-o", "--oads",
            action="append", dest="oads_list", default=None,
            help=(
                "For mode 'create' only. Define a new OADS url for the new "
                "collection."
            )
        ),
        make_option("-n", "--nga",
            action="append", dest="nga_list", default=None,
            help=(
                "For mode 'create' only. Define a new ngA url for the new "
                "collection."
            )
        )
    )

    require_group = "minv_g_app_engineers"

    args = (
        'MISSION/FILE-TYPE [ -c | -d | -l ] '
        '[ -o <oads-url> [ -o <oads-url> ... ]] '
        '[ -n <nga-url> [ -n <nga-url> ... ]] '
    )

    help = (
        'Create or delete or list collections. '
        'Requires membership of group "minv_g_app_engineers".'
    )

    @transaction.atomic
    def handle_authorized(self, *args, **options):
        mode = options["mode"] or "create"

        mission = None
        file_type = None

        if mode in ("create", "delete"):
            if not args:
                raise CommandError(
                    "For mode create and delete a collection identifier is "
                    "necessary."
                )

            try:
                mission, file_type = args[0].split("/")
            except:
                raise CommandError("Invalid Collection specifier '%s'" % args[0])

        if mode == "create":
            oads_list = options["oads_list"] or []
            nga_list = options["nga_list"] or []

            try:
                collection = models.Collection.objects.create(
                    mission=mission, file_type=file_type
                )
                print("Adding collection '%s'." % collection)
            except IntegrityError:
                raise CommandError(
                    "A collection with mission '%s' and file type '%s' already "
                    "exists." % (mission, file_type)
                )

            for url in nga_list:
                location = models.Location.objects.create(
                    collection=collection, location_type="nga", url=url
                )
                print("Adding location '%s' to collection." % location)

            for url in oads_list:
                location = models.Location.objects.create(
                    collection=collection, location_type="oads", url=url
                )
                print("Adding location '%s' to collection." % location)

        elif mode == "delete":
            try:
                collection = models.Collection.objects.get(
                    mission=mission, file_type=file_type
                )

            except models.Collection.DoesNotExist:
                raise CommandError(
                    "No such collection with mission '%s' and file type '%s'."
                    % (mission, file_type)
                )

            print("Deleting collection '%s'" % collection)
            collection.delete()
            if options.get("purge"):
                # TODO: delete configuration folder as-well
                pass

        elif mode == "list":
            for collection in models.Collection.objects.all():
                print(collection)
