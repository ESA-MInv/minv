from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

from minv.tasks.harvest import harvest


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option("-m", "--mission", dest="mission"),
        make_option("-f", "--file-type", dest="file_type"),
        make_option("-u", "--url", dest="urls",
            action="append", help="The harvesting location to harvest.")
    )

    args = '-m MISSION -f FILE TYPE -u <location-url> [ -u <location-url> ... ]'

    help = 'Harvest the whole collection or specific locations of a collection.'

    def handle(self, *args, **options):
        if not options["urls"]:
            raise CommandError("No location URLs specified.")

        for url in options["urls"]:
            try:
                harvest(
                    options["mission"], options["file_type"], url
                )
            except Exception as exc:
                raise CommandError(
                    "Failed to harvest location %s. Error was: %s" % (url, exc)
                )
