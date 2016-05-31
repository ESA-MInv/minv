from optparse import make_option
import os
from os.path import join, splitext, getmtime
import tempfile
import shutil
from uuid import uuid4
import subprocess
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from minv.commands import MinvCommand
from minv.inventory import models
from minv.config import (
    GlobalReader,
    check_global_configuration,
    global_configuration_changes
)
from minv.inventory.collection.config import (
    CollectionConfigurationReader,
    check_collection_configuration,
    collection_configuration_changes
)


def create_temporary_copy(path):
    temp_path = join(tempfile.gettempdir(), uuid4().hex)
    shutil.copy2(path, temp_path)
    return temp_path


class Command(MinvCommand):
    option_list = BaseCommand.option_list + (
        make_option("-g", "--global",
            action="store_true", dest="global", default=False
        ),
        make_option("-e", "--edit",
            action="store_const", dest="mode", const="edit", default="edit"
        ),
        make_option("-i", "--import",
            action="store_const", dest="mode", const="import"
        ),
        make_option("-c", "--check",
            action="store_const", dest="mode", const="check"
        ),
    )

    require_group = "minv_g_app_engineers"

    args = (
        '[ -g | MISSION/FILE-TYPE ] [ -e | -i | -c ]'
    )

    help = (
        'Edit, check and import configuration for collections or the system. '
        'Requires membership of group "minv_g_app_engineers".'
    )

    def handle_authorized(self, *args, **options):
        global_config = options.get("global")
        mode = options["mode"]

        collection = None

        if global_config:
            pass
        else:
            try:
                mission, file_type = args[0].split("/")
                collection = models.Collection.objects.get(
                    mission=mission, file_type=file_type
                )

            except models.Collection.DoesNotExist:
                raise CommandError(
                    "No such collection with mission '%s' and file type '%s'."
                    % (mission, file_type)
                )
            except:
                raise CommandError("Invalid Collection specifier '%s'" % args[0])

        if mode == "edit":
            self.handle_edit(collection)

        elif mode == "import":
            try:
                filename = args[0 if not collection else 1]
            except IndexError:
                raise CommandError("No import configuration filename given.")

            self.handle_import(filename, collection)

        elif mode == "check":
            self.handle_check(collection)

    def _check_errors(self, path, old_path, collection):
        # check for errors
        if collection:
            reader = CollectionConfigurationReader(path)
            errors = check_collection_configuration(reader)
        else:
            reader = GlobalReader(path)
            errors = check_global_configuration(reader)

        if errors:
            self.error(
                "Configuration contains errors:\n   - %s"
                % ("\n   - ".join(errors))
            )
        return errors

    def _print_changes(self, old_path, new_path, collection):
        if collection:
            old = CollectionConfigurationReader(old_path)
            new = CollectionConfigurationReader(new_path)
            changes = collection_configuration_changes(old, new)
        else:
            old = GlobalReader(old_path)
            new = GlobalReader(new_path)
            changes = global_configuration_changes(old, new)

        if changes:
            self.info(
                "Detected changes in the configuration:\n   - %s"
                % ("\n   - ".join(
                    "%s: %s --> %s" % (field, change[0], change[1])
                    for field, change in changes.items()
                ))
            )

        if collection:
            has_mapping_changes = False
            for key in changes:
                has_mapping_changes = key.startswith("metadata_mapping")
                break
            if has_mapping_changes:
                print(
                    "Please reload the index files in the database using "
                    "'minv reload %s'" % collection
                )
        elif not collection and changes:
            print(
                "Please restart the webserver and the minv service to reload "
                "the configuration"
            )

    def _backup_config(self, path):
        root, ext = splitext(path)
        timestamp = datetime.fromtimestamp(getmtime(path)).replace(
            microsecond=0, tzinfo=None
        )
        timestr = timestamp.isoformat("T").replace(":", "")
        backup_path = "%s-%s%s" % (
            root, timestr, ext
        )
        shutil.move(path, backup_path)
        self.info("Backed up old configuration at '%s'" % backup_path)

    def handle_edit(self, collection=None):
        if collection:
            path = join(collection.config_dir, "collection.conf")
        else:
            path = "/etc/minv/minv.conf"

        copy_path = create_temporary_copy(path)

        cmd = os.environ.get('EDITOR', 'vi') + ' ' + copy_path
        subprocess.call(cmd, shell=True)

        if self._check_errors(copy_path, path, collection):
            os.unlink(copy_path)
            raise CommandError("Failed to edit configuration %s" % path)

        # check for changes
        self._print_changes(path, copy_path, collection)

        # backup old config
        self._backup_config(path)

        # store new config
        shutil.move(copy_path, path)

        if collection:
            self.info(
                "Successfully edited configuration for collection %s."
                % collection
            )
        else:
            self.info("Successfully edited global configuration.")

    def handle_import(self, import_path, collection=None):
        if collection:
            path = join(collection.config_dir, "collection.conf")
        else:
            path = "/etc/minv/minv.conf"

        if self._check_errors(import_path, path, collection):
            raise CommandError("Failed to import configuration %s" % import_path)

        # check for changes
        self._print_changes(path, import_path, collection)

        # backup old config
        self._backup_config(path)

        # store new config
        shutil.copy2(import_path, path)

        if collection:
            self.info(
                "Successfully imported configuration for collection %s from %s."
                % (collection, import_path)
            )
        else:
            self.info(
                "Successfully imported global configuration file from %s."
                % (import_path)
            )

    def handle_check(self, collection=None):
        if collection:
            path = join(collection.config_dir, "collection.conf")
        else:
            path = "/etc/minv/minv.conf"

        if self._check_errors(path, path, collection):
            raise CommandError("Check for configuration file %s failed" % path)

        if collection:
            self.info(
                "Check of configuration for collection %s passed." % collection
            )
        else:
            self.info("Check of global configuration passed.")
