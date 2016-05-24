from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

from minv.commands import MinvCommand
from minv.tasks.registry import registry


class Command(MinvCommand):
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

    args = '[ MISSION/FILE-TYPE ] <filename>'

    help = 'Import the specified archive.'

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
