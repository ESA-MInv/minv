from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

from minv.commands import CollectionCommand
from minv.tasks.registry import registry


class Command(CollectionCommand):
    option_list = BaseCommand.option_list + (
        make_option("-o", "--output", dest="output", default=None),
        make_option("--configuration", dest="configuration",
            action="store_true", default=True
        ),
        make_option("--no-configuration", dest="configuration",
            action="store_false", default=True
        ),
        make_option("--data", dest="data",
            action="store_true", default=True
        ),
        make_option("--no-data", dest="data",
            action="store_false", default=True
        )
    )

    args = 'MISSION/FILE-TYPE [ -o <export-filename> ] ' \
           '[ --configuration | --no-configuration ] ' \
           '[ --data | --no-data ]'

    help = 'Export the configuration and/or data of the specified collection.'

    def handle_collection(self, collection, *args, **options):
        output = options["output"]
        registry.initialize()

        try:
            filename = registry.run(
                "export",
                mission=collection.mission,
                file_type=collection.file_type,
                filename=output,
                configuration=options["configuration"],
                data=options["data"]
            )
            print "Exported collection %s to %s" % (
                collection, filename
            )
        except Exception as exc:
            raise CommandError(
                "Failed to export collection %s to %s. Error was: %s" % (
                    collection, options["output"], exc
                )
            )
