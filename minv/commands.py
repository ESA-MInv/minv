from django.core.management.base import BaseCommand, CommandError

from minv.tasks.registry import registry
from minv.inventory import models


class AuthorizationError(Exception):
    pass


class MinvCommand(BaseCommand):
    require_group = None

    def handle(self, *args, **kwargs):
        registry.initialize()
        if self.require_group:
            # TODO: see if the user is in the right group

            # TODO: perform check
            self.authorize()

        return self.handle_authorized(*args, **kwargs)

    def authorize(self, require_group):
        # TODO: perform check

        grp_id = grp.getgrnam(self.require_group).gr_id
        
        pass

    def handle_authorized(self, *args, **kwargs):
        raise NotImplementedError


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
