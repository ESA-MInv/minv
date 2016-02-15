from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

from minv.inventory.ingest import ingest


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option("-m", "--mission", dest="mission"),
        make_option("-f", "--file-type", dest="file_type"),
        make_option("-u", "--url", dest="url")
    )

    args = '-m MISSION -f FILE TYPE -u URL <index-file-name> ' \
           '[<index-file-name> ...]'

    help = 'Ingest the given index files.'

    def handle(self, *args, **options):

        for index_file_name in args:
            try:
                ingest(
                    options["mission"], options["file_type"], options["url"],
                    index_file_name
                )
            except Exception as exc:
                raise CommandError(
                    "Failed to ingest index file '%s'. Error was: %s"
                    % (index_file_name, exc)
                )
