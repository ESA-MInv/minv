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
from getpass import getpass, getuser

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.auth import models

from minv.commands import MinvCommand


class Command(MinvCommand):
    option_list = BaseCommand.option_list + (
        make_option("-g", "--group", dest="groups",
            action="append", default=None,
            help=(
                "Define a group that the new user shall be included in. "
                "Available groups are: minv_g_app_engineers, "
                "minv_g_app_administrators, minv_g_operators, and "
                "minv_g_security_engineers."
            )
        ),
    )

    require_group = "minv_g_app_administrators"

    args = '-g <group> [ -g <group> ... ] <username>'

    help = (
        'Create users for the Web interface. '
        'Requires membership of group "minv_g_app_administrators".'
    )

    @transaction.atomic
    def handle(self, *args, **options):
        groups = options.get("groups", [])
        if len(args) == 1:
            username = args[0]
        elif len(args) < 1:
            username = getuser()
        else:
            raise CommandError("Must specify exactly one username.")

        pwd1 = getpass(prompt="Password: ")
        pwd2 = getpass(prompt="Password (again): ")

        if pwd1 != pwd2:
            raise CommandError("Passwords do not match.")

        try:
            user = models.User.objects.create_user(username, password=pwd1)
        except:
            raise CommandError("User '%s' already exists" % username)

        for groupname in groups:
            try:
                group = models.Group.objects.get(name=groupname)
                user.groups.add(group)
            except models.Group.DoesNotExist:
                raise CommandError(
                    "No such group '%s'. Available groups are: %s" % (
                        groupname, ", ".join(
                            "'%s'" % name for name in
                            models.Group.objects.all().values_list(
                                "name", flat=True
                            )
                        )
                    )
                )

        print("User '%s' created." % username)
