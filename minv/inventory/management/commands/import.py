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
