from optparse import make_option
import json
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.timezone import now

from minv.utils import parse_duration, total_seconds
from minv.inventory import models
from minv.tasks import models as task_models
from minv.tasks.daemon import send_reload_schedule


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option("-a", "--all", dest="all",
            action="store_true", default=False,
            help="Schedule all locations from all collections."
        ),
        make_option("-m", "--mission", dest="mission"),
        make_option("-f", "--file-type", dest="file_type"),
        make_option("-u", "--url", dest="url"),

        make_option("-n", "--now", dest="now",
            action="store_true", default=False,
            help="Schedule the harvesting as soon as possible."
        ),
        make_option("-i", "--in", dest="in",
            help="Schedule the task in the specified interval."
        ),
    )

    args = (
        '-a | ( -m MISSION -f FILE TYPE [ -u <url> ] ) '
        '[ -n | -i <duration-string> ]'
    )

    help = (
        'Schedule the harvesting of a collections harvesting locations. '
        'By default the jobs are scheduled in the time specified in the '
        'collections "harvesting_interval" configuration.'
    )

    @transaction.atomic
    def handle(self, *args, **options):
        if options.get("all"):
            locations = list(models.Location.objects.all())

        else:
            mission = options["mission"]
            file_type = options["file_type"]
            url = options["url"]

            if not mission or not file_type:
                raise CommandError("No collection specified.")

            collection = models.Collection.objects.get(
                mission=mission, file_type=file_type
            )

            if url:
                locations = [collection.locations.get(url=url)]
            else:
                locations = list(collection.locations.all())

        # get the duration when the harvest shall be scheduled
        if options.get("now"):
            interval = timedelta(0.0)
        elif options.get("in"):
            interval = parse_duration(options["in"])
        else:
            # get the harvesting interval from collection configuration
            interval = None

        # remove all scheduled items
        scheduled_jobs = set(task_models.ScheduledJob.objects.all())
        for location in locations:
            to_delete_jobs = set([
                scheduled_job
                for scheduled_job in scheduled_jobs
                if
                scheduled_job.argument_values.get("mission") ==
                location.collection.mission and
                scheduled_job.argument_values.get("file_type") ==
                location.collection.file_type and
                scheduled_job.argument_values.get("url") == location.url
            ])

            for scheduled_job in to_delete_jobs:
                args = scheduled_job.argument_values
                print(
                    "Removing previous scheduled job for "
                    "{mission}/{file_type} {url}".format(**args)
                )
                scheduled_job.delete()

            scheduled_jobs -= to_delete_jobs

        current_datetime = now()

        # create a scheduled item for each location
        for location in locations:
            args = {
                "mission": location.collection.mission,
                "file_type": location.collection.file_type,
                "url": location.url
            }

            if interval is None:
                interval = location.collection.configuration.harvest_interval

            print(
                "Creating scheduled job for %s/%s %s in %.1f seconds." % (
                    args["mission"], args["file_type"], args["url"],
                    total_seconds(interval)
                )
            )
            task_models.ScheduledJob.objects.create(
                task="harvest", when=current_datetime + interval,
                arguments=json.dumps(args)
            )

        # inform the daemon
        try:
            send_reload_schedule()
        except Exception as exc:
            if options.get("traceback"):
                raise
            raise CommandError(
                "Failed to send 'reload' message to daemon. Error was '%s'" % exc
            )
