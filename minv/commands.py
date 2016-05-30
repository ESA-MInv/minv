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
            self.authorize(self.require_group)

        self.info("Running command '%s'" % self.get_command_name())
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
                % (self.get_command_name())
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
            print(message)

    def info(self, message):
        logger.info(message)
        if self.verbosity:
            print(message)

    def warning(self, message):
        logger.warning(message)
        if self.verbosity:
            print(message)

    def error(self, message):
        logger.error(message)
        if self.verbosity:
            print(message)


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
