from optparse import make_option
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.timezone import now

from minv.commands import MinvCommand
from minv.utils import parse_duration, total_seconds
from minv.inventory import models
from minv.tasks import models as task_models
from minv.tasks.api import schedule_many, send_reload_schedule


class Command(MinvCommand):
    option_list = BaseCommand.option_list + (
        make_option("-c", "--create", dest="mode",
            action="store_const", const="create", default="create",
            help="Set the mode to 'create' (the default). Used to create new "
                 "scheduled tasks"
        ),
        make_option("-r", "--remove", dest="mode",
            action="store_const", const="remove", default="create",
            help="Set the mode to 'remove'. Used to remove scheduled tasks."
        ),

        make_option("-t", "--task", dest="task",
            default="harvest",
            help="The task to schedule. Defaults to 'harvest', other options "
                 "are 'export'."
        ),

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
    )

    require_group = "minv_g_operators"

    args = (
        '[ -c | -r ] [ -t <task-name> ] -a | ( MISSION/FILE-TYPE [ -u <url> ] ) '
        '[ -n | -i <duration-string> ]'
    )

    help = (
        'Schedule an export or harvesting task or remove such a '
        'scheduled task. Once run, the jobs are repeated in the configured '
        'timespan depending on the task: "export_interval" and '
        '"harvest_interval" in the collections configuration. '
        'Requires membership of group "minv_g_operators".'
    )

    @transaction.atomic
    def handle_authorized(self, *args, **options):
        task = options["task"]
        if task not in ("harvest", "export", "backup"):
            raise CommandError("Invalid task name '%s'" % task)

        mode = options.pop("mode")

        # get the duration when the task shall be scheduled
        if options.get("now"):
            interval = timedelta(0.0)
        elif options.get("in"):
            interval = parse_duration(options["in"])
        else:
            # get the harvesting interval from collection configuration
            interval = None

        if task == "harvest":
            items = self.handle_harvest(mode, interval, *args, **options)
        elif task == "export":
            items = self.handle_export(mode, interval, *args, **options)
        else:
            raise CommandError("Unknown task '%s'." % task)

        # inform the daemon
        try:
            if items:
                schedule_many(items)
            else:
                send_reload_schedule()
        except Exception as exc:
            if options.get("traceback"):
                raise
            raise CommandError(
                "Failed to send 'reload' message to daemon. Error was '%s'"
                % exc
            )

    def handle_harvest(self, mode, interval, *args, **options):
        if options.get("all"):
            locations = list(models.Location.objects.all())

        else:
            try:
                mission, file_type = args[0].split("/")
            except:
                raise CommandError(
                    "Invalid collection specifier '%s'" % args[0]
                )

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

        # remove all scheduled items that fit the current one
        scheduled_jobs = set(
            task_models.ScheduledJob.objects.filter(task="harvest")
        )
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
                self.info(
                    "Removing scheduled job for "
                    "{mission}/{file_type} {url}".format(**args)
                )
                scheduled_job.delete()

            scheduled_jobs -= to_delete_jobs

        if mode == "create":
            # create a scheduled item for each location
            items = []
            current_datetime = now()

            for location in locations:
                args = {
                    "mission": location.collection.mission,
                    "file_type": location.collection.file_type,
                    "url": location.url,
                    "reschedule": True
                }

                if interval is None:
                    interval = location.collection.configuration.harvest_interval

                self.info(
                    "Creating scheduled job for %s/%s %s in %.1f seconds." % (
                        args["mission"], args["file_type"], args["url"],
                        total_seconds(interval)
                    )
                )
                items.append(("harvest", current_datetime + interval, args))

                return items

    def handle_export(self, mode, interval, *args, **options):
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

        # remove all scheduled items that fit the current one
        scheduled_jobs = set(
            task_models.ScheduledJob.objects.filter(task="export")
        )
        for collection in collections:
            to_delete_jobs = set([
                scheduled_job
                for scheduled_job in scheduled_jobs
                if
                scheduled_job.argument_values.get("mission") ==
                collection.mission and
                scheduled_job.argument_values.get("file_type") ==
                collection.file_type
            ])

            for scheduled_job in to_delete_jobs:
                args = scheduled_job.argument_values
                self.info(
                    "Removing scheduled job for "
                    "{mission}/{file_type}".format(**args)
                )
                scheduled_job.delete()

            scheduled_jobs -= to_delete_jobs

        if mode == "create":
            # create a scheduled item for each location
            items = []
            current_datetime = now()

            for collection in collections:
                args = {
                    "mission": collection.mission,
                    "file_type": collection.file_type,
                    "reschedule": True
                }

                if interval is None:
                    interval = collection.configuration.export_interval

                self.info(
                    "Creating scheduled job for %s/%s in %.1f seconds." % (
                        args["mission"], args["file_type"],
                        total_seconds(interval)
                    )
                )
                items.append(("export", current_datetime + interval, args))

            return items
