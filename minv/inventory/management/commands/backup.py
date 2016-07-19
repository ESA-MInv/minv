from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

from minv.commands import MinvCommand
from minv.tasks.registry import registry


class Command(MinvCommand):
    option_list = BaseCommand.option_list + (
        make_option("-l", "--logs", dest="logs",
            default=False, action="store_true",
            help="Backup log files."
        ),
        make_option("-c", "--config", dest="config",
            default=False, action="store_true",
            help="Backup configuration files."
        ),
        make_option("-a", "--app", dest="app",
            default=False, action="store_true",
            help="Backup application software."
        ),

        make_option("-d", "--diff", dest="diff",
            default=None,
            help="Make a differential backup to the specified file."
        ),
        make_option("-i", "--incremental", dest="incr",
            default=None,
            help=(
                "Make an incremental backup, saving everything newer than the "
                "specified ISO 8601 timestamp."
            )
        ),
        make_option("-o", "--output", dest="output",
            default=None,
            help=(
                "Define the output filename. By default a filename is generated."
            )
        ),
    )

    require_group = "minv_g_app_administrators"

    args = (
        '[-l] [-c] [-a] [-d <diff-backup>] [-i <timestamp>] [-o <filename>]'
    )

    help = (
        'Make a backup from either any or all of the MInv logs, configuration, '
        'and software application. The backup is either "full" (the default), '
        'differential, or incremental. '
        'Requires membership of group "minv_g_app_administrator".'
    )

    def handle_authorized(self, *args, **options):
        logs = options["logs"]
        config = options["config"]
        app = options["app"]

        if not logs and not config and not app:
            raise CommandError(
                "Must specify at least one of --logs, --config, or --app."
            )

        diff = options["diff"]
        incr = options["incr"]

        try:
            path = registry.run("backup",
                logs=logs, config=config, app=app, diff=diff, incr=incr,
                out_path=options.get("output")
            )
            self.info("Backup successful. Stored at '%s'" % path)
        except Exception as exc:
            if options.get("traceback"):
                raise
            self.error("Unable to perform backup. Error was: %s" % exc)
