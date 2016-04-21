from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

from minv.inventory.collection.export import import_collection


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option("-m", "--mission", dest="mission",
            help="Optional. The 'mission' of the to be imported collection. "
                 "By default the 'mission' is extracted from the archive."
        ),
        make_option("-f", "--file-type", dest="file_type",
            help="Optional. The 'file type' of the to be imported collection. "
                 "By default the 'file type' is extracted from the archive."
        )
    )

    args = '[ -m MISSION -f FILE TYPE ] <filename>'

    help = 'Import the specified archive.'

    def handle(self, *args, **options):
        if len(args) > 1:
            raise CommandError("Too many files specified")
        elif not args:
            raise CommandError("Missing archive filename")

        filename = args[0]
        try:
            collection = import_collection(
                filename, options["mission"], options["file_type"]
            )
            print "Sucessfully imported collection %s" % collection
        except Exception as exc:
            raise CommandError(
                "Failed to import archive '%s'. Error was: %s"
                % (filename, exc)
            )
