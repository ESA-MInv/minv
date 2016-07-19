from django.core.management.base import BaseCommand, CommandError

from minv.commands import MinvCommand
from minv.inventory.backup import restore


class Command(MinvCommand):
    option_list = BaseCommand.option_list + ()

    require_group = "minv_g_app_administrators"

    args = '<filename>'

    help = (
        'Restore the contents of the backup archive. '
        'Requires membership of group "minv_g_app_administrator".'
    )

    def handle_authorized(self, *args, **options):
        if len(args) < 1:
            raise CommandError("No backup filename specified.")

        filename = args[0]

        try:
            restore(filename)
            self.info("Successfully restored backup '%s'." % filename)
        except Exception as exc:
            self.error(
                "Unable to restore backup '%s' backup. Error was: %s"
                % (filename, exc)
            )
            if options.get("traceback"):
                raise
