from django.core.management.base import BaseCommand

from minv.tasks.daemon import Daemon


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
    )

    args = ''

    help = 'Run the MInv daemon.'

    def handle(self, use_reloader=False, *args, **options):
        daemon = Daemon()
        daemon.run()
