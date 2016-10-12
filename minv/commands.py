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


import sys
import os
import grp
import logging

from django.core.management.base import BaseCommand, CommandError

from minv.tasks.registry import registry
from minv.inventory import models

logger = logging.getLogger(__name__)


class AuthorizationError(Exception):
    pass


class MinvCommand(BaseCommand):
    require_group = None

    def handle(self, *args, **options):
        registry.initialize()
        self.verbosity = options.get("verbosity", 1)
        if self.require_group:
            # self.authorize(self.require_group)
            pass

        self.info(
            "User '%s' is running command '%s' with "
            "arguments %r and options %r" % (
                self.get_user_name(), self.get_command_name(),
                args, options
            )
        )
        return self.handle_authorized(*args, **options)

    def get_command_name(self):
        return (self.__class__.__module__).rpartition(".")[-1]

    def get_user_name(self):
        """ Get the user name (behind SUDO).
        """
        return os.environ.get("USER")

    def authorize(self, require_group):
        """ Method to authorize a user
        """

        username = self.get_user_name()
        self.debug("Authorizing user %s. Required group: %s" % (
            username, require_group)
        )
        group = grp.getgrnam(self.require_group)

        if not self.get_user_name() in group[3]:
            self.warning(
                "User %s was not authorized to run the command '%s'."
                % (username, self.get_command_name())
            )
            raise CommandError(
                "User %s is not authorized to run this command."
                % (self.get_user_name())
            )
        else:
            self.info(
                "User %s is authorized to run the command '%s'."
                % (username, self.get_command_name())
            )

    def handle_authorized(self, *args, **options):
        raise NotImplementedError

    def debug(self, message):
        logger.debug(message)
        if self.verbosity > 1:
            sys.stderr.write(message)

    def info(self, message):
        logger.info(message)
        if self.verbosity:
            sys.stderr.write(message)
            sys.stderr.write("\n")

    def warning(self, message):
        logger.warning(message)
        if self.verbosity:
            sys.stderr.write(message)
            sys.stderr.write("\n")

    def error(self, message):
        logger.error(message)
        if self.verbosity:
            sys.stderr.write(message)
            sys.stderr.write("\n")


class CollectionCommand(MinvCommand):

    def handle_authorized(self, *args, **kwargs):
        """ Check that the first positional argument is a collection specifier.
        """
        if not args:
            raise CommandError("Missing collection identifier MISSION/FILE_TYPE")

        try:
            collection_def = args[0]
            mission, file_type = collection_def.split("/")
        except:
            raise CommandError(
                "Invalid collection identifier '%s'. Must be MISSION/FILE_TYPE"
                % collection_def
            )

        try:
            collection = models.Collection.objects.get(
                mission=mission, file_type=file_type
            )
        except models.Collection.DoesNotExist:
            raise CommandError("No such collection %s/%s" % (mission, file_type))

        self.handle_collection(collection, *args[1:], **kwargs)
