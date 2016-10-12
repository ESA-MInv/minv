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


from django.core.management.base import CommandError

from minv.commands import MinvCommand
from minv.tasks.registry import registry


class Command(MinvCommand):
    require_group = "minv_g_app_engineers"

    args = '[ MISSION/FILE-TYPE ] <filename>'

    help = (
        'Import the specified archive. '
        'Requires membership of group "minv_g_app_engineers".'
    )

    def handle_authorized(self, *args, **options):
        if len(args) > 2:
            raise CommandError("Too many files specified")
        elif not args:
            raise CommandError("Missing archive filename")

        filename = args[-1]

        mission = None
        file_type = None

        if len(args) == 2:
            mission, file_type = args[0].split("/")
        try:
            collection = registry.run(
                "import",
                filename=filename,
                mission=mission,
                file_type=file_type
            )
            print "Sucessfully imported collection %s" % collection
        except Exception as exc:
            if options.get("traceback"):
                raise
            raise CommandError(
                "Failed to import archive '%s'. Error was: %s"
                % (filename, exc)
            )
