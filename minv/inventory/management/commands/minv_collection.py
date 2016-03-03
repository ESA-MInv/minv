from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.utils import IntegrityError

from minv.inventory import models


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option("-c", "--create",
            action="store_const", dest="mode", const="create", default="create"
        ),
        make_option("-d", "--delete",
            action="store_const", dest="mode", const="delete"
        ),
        make_option("-l", "--list",
            action="store_const", dest="mode", const="list"
        ),
        make_option("-m", "--mission", dest="mission"),
        make_option("-f", "--file-type", dest="file_type"),
        make_option("-o", "--oads",
            action="append", dest="oads_list", default=None
        ),
        make_option("-n", "--nga",
            action="append", dest="nga_list", default=None
        ),
    )

    args = (
        '-m MISSION -f FILE TYPE [-c | -d | -l] '
        '[-o <oads-url> [-o <oads-url> ... ]] '
        '[-n <nga-url> [-n <nga-url> ... ]] '
    )

    help = 'Create or delete collections.'

    @transaction.atomic
    def handle(self, *args, **options):
        mode = options["mode"] or "create"

        mission = options["mission"]
        file_type = options["file_type"]

        if mode in ("create", "delete"):
            if not mission:
                raise CommandError("Missing mandatory parameter 'mission'.")

            if not file_type:
                raise CommandError("Missing mandatory parameter 'file-type'.")

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
                    collection=collection, location_type="ngA", url=url
                )
                print("Adding location '%s' to collection." % location)

            for url in oads_list:
                location = models.Location.objects.create(
                    collection=collection, location_type="OADS", url=url
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

        elif mode == "list":
            for collection in models.Collection.objects.all():
                print(collection)
