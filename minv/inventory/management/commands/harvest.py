from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

from minv.tasks.harvest import harvest


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option("-m", "--mission", dest="mission"),
        make_option("-f", "--file-type", dest="file_type"),
        make_option("-u", "--url", dest="url")
    )

    args = '-m MISSION -f FILE TYPE -u URL <location-url> ' \
           '[<index-file-name> ...]'

    help = 'Harvest the whole collection or specific locations of a collection.'

    def handle(self, *args, **options):
        harvest(
            options["mission"], options["file_type"], options["url"]
        )
