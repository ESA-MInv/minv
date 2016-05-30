from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

from minv.commands import CollectionCommand
from minv.inventory.ingest import ingest


class Command(CollectionCommand):
    option_list = BaseCommand.option_list + (
        make_option("-m", "--mission", dest="mission"),
        make_option("-f", "--file-type", dest="file_type"),
        make_option("-u", "--url", dest="url")
    )

    require_group = "minv_g_operators"

    args = 'MISSION/FILE-TYPE -u URL <index-file-name> ' \
           '[<index-file-name> ...]'

    help = (
        'Ingest the given index files. '
        'Requires membership of group "minv_g_operators".'
    )

    def handle_collection(self, collection, *args, **options):

        for index_file_name in args:
            try:
                # TODO: print number of records ingested
                ingest(
                    collection.mission, collection.file_type, options["url"],
                    index_file_name
                )
            except Exception as exc:
                raise CommandError(
                    "Failed to ingest index file '%s'. Error was: %s"
                    % (index_file_name, exc)
                )
