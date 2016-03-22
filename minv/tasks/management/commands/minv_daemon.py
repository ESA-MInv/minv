# from optparse import make_option

from django.core.management.base import BaseCommand

from minv.tasks.daemon import Daemon


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
    )

    args = ''

    help = 'Run the MInv daemon.'

    def handle(self, *args, **options):
        Daemon().run()
