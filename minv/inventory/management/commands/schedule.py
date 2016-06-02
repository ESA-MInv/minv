from optparse import make_option
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.timezone import now

from minv.commands import MinvCommand
from minv.utils import parse_duration, total_seconds
from minv.inventory import models
from minv.tasks import models as task_models
from minv.tasks.api import schedule_many


class Command(MinvCommand):
    option_list = BaseCommand.option_list + (
        make_option("-a", "--all", dest="all",
            action="store_true", default=False,
            help="Schedule all locations from all collections."
        ),
        make_option("-u", "--url", dest="urls", action="append", default=None,
            help="Specify that a location shall be scheduled for harvest."
        ),
        make_option("-n", "--now", dest="now",
            action="store_true", default=False,
            help="Schedule the task as soon as possible."
        ),
        make_option("-i", "--in", dest="in",
            help=(
                "Schedule the task in the specified interval. Use ISO 8601 "
                "period expressions. e.g: PT5M"
            )
        ),
        make_option("-t", "--task", dest="task",
            default="harvest",
            help="The task to schedule. Defaults to 'harvest', other options "
                 "are 'export' and 'backup'."
        )
    )

    require_group = "minv_g_operators"

    args = (
        '-a | ( MISSION/FILE-TYPE [ -u <url> ] ) '
        '[ -n | -i <duration-string> ]'
    )

    help = (
        'Schedule the harvesting of a collections harvesting locations. '
        'By default, the jobs are scheduled in the time specified in the '
        'collections "harvesting_interval" configuration. '
        'Requires membership of group "minv_g_operators".'
    )

    @transaction.atomic
    def handle_authorized(self, *args, **options):
        task = options["task"]
        if task not in ("harvest", "export", "backup"):
            raise CommandError("Invalid task name '%s'" % task)

        if task == "harvest":
            return self.handle_harvest(*args, **options)
        elif task == "export":
            return self.handle_export(*args, **options)
        else:
            raise CommandError("Backup not implemented.")

    def handle_harvest(self, *args, **options):
        if options.get("all"):
            locations = list(models.Location.objects.all())

        else:
            try:
                mission, file_type = args[0].split("/")
            except:
                raise CommandError("Invalid collection specifier '%s'" % args[0])

            try:
                collection = models.Collection.objects.get(
                    mission=mission, file_type=file_type
                )
            except models.Collection.DoesNotExist:
                raise CommandError("No such collection %s/%s." % (
                    mission, file_type
                ))

            urls = options.get("urls")
            if urls:
                locations = [
                    collection.locations.get(url=url)
                    for url in urls
                ]
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

        # remove all scheduled items that fit the current one
        scheduled_jobs = set(task_models.ScheduledJob.objects.all())
        for location in locations:
            to_delete_jobs = set([
                scheduled_job
                for scheduled_job in scheduled_jobs
                if
                scheduled_job.task == "harvest" and
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
        items = []
        for location in locations:
            args = {
                "mission": location.collection.mission,
                "file_type": location.collection.file_type,
                "url": location.url,
                "reschedule": True
            }

            if interval is None:
                interval = location.collection.configuration.harvest_interval

            print(
                "Creating scheduled job for %s/%s %s in %.1f seconds." % (
                    args["mission"], args["file_type"], args["url"],
                    total_seconds(interval)
                )
            )
            items.append(("harvest", current_datetime + interval, args))

        # inform the daemon
        try:
            schedule_many(items)
        except Exception as exc:
            if options.get("traceback"):
                raise
            raise CommandError(
                "Failed to send 'reload' message to daemon. Error was '%s'" % exc
            )

    def handle_export(self, *args, **options):
        if options.get("all"):
            collections = list(models.Collection.objects.all())

        else:
            try:
                mission, file_type = args[0].split("/")
            except:
                raise CommandError("Invalid collection specifier '%s'" % args[0])

            try:
                collections = [
                    models.Collection.objects.get(
                        mission=mission, file_type=file_type
                    )
                ]
            except models.Collection.DoesNotExist:
                raise CommandError("No such collection %s/%s." % (
                    mission, file_type
                ))

        # get the duration when the harvest shall be scheduled
        if options.get("now"):
            interval = timedelta(0.0)
        elif options.get("in"):
            interval = parse_duration(options["in"])
        else:
            # get the harvesting interval from collection configuration
            interval = None

        # remove all scheduled items that fit the current one
        scheduled_jobs = set(task_models.ScheduledJob.objects.all())
        for collection in collections:
            to_delete_jobs = set([
                scheduled_job
                for scheduled_job in scheduled_jobs
                if
                scheduled_job.task == "export" and
                scheduled_job.argument_values.get("mission") ==
                collection.mission and
                scheduled_job.argument_values.get("file_type") ==
                collection.file_type
            ])

            for scheduled_job in to_delete_jobs:
                args = scheduled_job.argument_values
                print(
                    "Removing previous scheduled job for "
                    "{mission}/{file_type}".format(**args)
                )
                scheduled_job.delete()

            scheduled_jobs -= to_delete_jobs

        current_datetime = now()

        # create a scheduled item for each location
        items = []
        for collection in collections:
            args = {
                "mission": collection.mission,
                "file_type": collection.file_type,
                "reschedule": True
            }

            if interval is None:
                interval = collection.configuration.export_interval

            print(
                "Creating scheduled job for %s/%s in %.1f seconds." % (
                    args["mission"], args["file_type"],
                    total_seconds(interval)
                )
            )
            items.append(("export", current_datetime + interval, args))

        # inform the daemon
        try:
            schedule_many(items)
        except Exception as exc:
            if options.get("traceback"):
                raise
            raise CommandError(
                "Failed to send 'reload' message to daemon. Error was '%s'" % exc
            )
