from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

from minv.inventory.collection.export import import_collection


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option("-m", "--mission", dest="mission"),
        make_option("-f", "--file-type", dest="file_type")
    )

    args = '-m MISSION -f FILE TYPE <filename>'

    help = 'Import the specified archive.'

    def handle(self, *args, **options):
        print args
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
            raise
            raise CommandError(
                "Failed to import archive '%s'. Error was: %s"
                % (filename, exc)
            )
