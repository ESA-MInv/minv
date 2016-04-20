from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

from minv.inventory.collection.export import export_collection


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option("-m", "--mission", dest="mission"),
        make_option("-f", "--file-type", dest="file_type"),
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

    args = '-m MISSION -f FILE TYPE [ -o <export-filename> ] ' \
           '[ --configuration | --no-configuration ] ' \
           '[ --data | --no-data ]'

    help = 'Export the configuration and/or data of the specified collection.'

    def handle(self, *args, **options):
        mission = options["mission"]
        file_type = options["file_type"]
        output = options["output"]

        if not mission or not file_type:
            raise CommandError("No collection specified.")

        try:
            filename = export_collection(
                mission, file_type, output,
                options["configuration"], options["data"]
            )
            print "Exported collection %s/%s to %s" % (
                mission, file_type, filename
            )
        except Exception as exc:
            raise CommandError(
                "Failed to export collection %s/%s to %s. Error was: %s" % (
                    options["mission"], options["file_type"], options["output"],
                    exc
                )
            )
