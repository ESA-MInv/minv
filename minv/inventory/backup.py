import os
from os.path import join, basename, getmtime
from zipfile import ZipFile
import glob
from contextlib import closing
from datetime import datetime
import json
import shutil
import logging

from django.utils.timezone import now, parse

import minv
from minv.inventory import models
from minv.tasks.registry import task
from minv.utils import safe_makedirs, parse_duration
from minv.config import (
    backup_config, GlobalReader,
    check_global_configuration
)
from minv.inventory.collection.config import (
    CollectionConfigurationReader,
    check_collection_configuration,
    collection_configuration_changes
)


BASE_PATH = "/srv/minv/backups/"

logger = logging.getLogger(__name__)


class BackupError(Exception):
    pass


@task
def backup(logs=False, config=False, app=False, diff=None, incr=None,
           out_path=None):
    """ Task function to perform the backup of the given items: logs,
    configuration and application (currently not supported). Backup can be full
    (the default), differential (specify path to other backup or a truthy value
    (will select the last backup)) or incremental (specify datetime or
    timedelta). An output path can be specified or one will be generated.
    Returns the path to the backup ZIP.
    """
    if not logs and not config and not app:
        raise BackupError("One of logs, config or app must be specified.")

    if diff and incr:
        raise BackupError(
            "Differential and incremental backups are mutially exclusive."
        )

    timestamp = now().strftime("%Y%m%d-%H%M%S")

    # assure that the backup path exists
    if not out_path:
        safe_makedirs(BASE_PATH)

    if diff:
        backupper = DifferentialBackup(logs, config, app, diff)
        out_path = out_path or join(BASE_PATH, "backup.diff.%s.zip" % timestamp)
    elif incr:
        backupper = IncrementalBackup(logs, config, app, incr)
        out_path = out_path or join(BASE_PATH, "backup.incr.%s.zip" % timestamp)
    else:
        backupper = FullBackup(logs, config, app)
        out_path = out_path or join(BASE_PATH, "backup.%s.zip" % timestamp)

    try:
        backupper.perform(out_path, timestamp)
    except Exception:
        try:
            os.unlink(out_path)
        except OSError:
            pass
        raise

    return out_path


def restore(in_path):
    """ Restore a previously backupped ZIP.
    """
    with closing(ZipFile(in_path)) as in_zip:
        manifest = json.loads(in_zip.read("manifest.json"))
        names = in_zip.namelist()

        if manifest["logs"]:
            # TODO: restore logs
            pass

        if manifest["config"]:
            # restore the global configuration
            errors = check_global_configuration(
                GlobalReader.from_fileobject(in_zip.open("config/minv.conf"))
            )
            if not errors:
                backup_config("/etc/minv/minv.conf")
                with open("/etc/minv/minv.conf", "w") as f:
                    shutil.copyfileobj(in_zip.open("config/minv.conf"), f)
                logger.info("Restored global configuration.")
            else:
                logger.warn(
                    "Could not restore global configuration due to errors:\n%s"
                    % ("\n".join(errors))
                )

            # restore all the collections configurations
            for name in names:
                if name.startswith("config/collections/"):
                    _restore_collection(in_zip, *name.split("/")[2:4])


def _restore_collection(in_zip, mission, file_type):
    collection, created = models.Collection.objects.get_or_create(
        mission=mission, file_type=file_type
    )

    location_descs = json.loads(in_zip.read(
        "config/collections/%s/locations.json" % collection)
    )
    for location_desc in location_descs:
        models.Location.objects.get_or_create(
            collection=collection, **location_desc
        )

    zip_config_path = "config/collections/%s/collection.conf" % collection
    errors = check_collection_configuration(
        CollectionConfigurationReader.from_fileobject(
            in_zip.open(zip_config_path)
        )
    )
    if not errors:
        backup_config(collection.config_path)
        with open(collection.config_path, "w") as f:
            shutil.copyfileobj(in_zip.open(zip_config_path), f)
        logger.info("Restored configuration for collection %s" % collection)
    else:
        logger.warn(
            "Could not restore global configuration due to errors:\n%s"
            % ("\n".join(errors))
        )


class FullBackup(object):
    """ Class to create full backups. Also serves as base class for other backup
    types.
    """
    def __init__(self, logs, config, app):
        self.logs = logs
        self.config = config
        self.app = app

    def decide_file(self, path, zip_path):
        return True

    def backup_file(self, path, zip_path, out_zip):
        if self.decide_file(path, zip_path):
            out_zip.write(path, zip_path)

    def get_manifest(self):
        return {"type": "full"}

    def perform(self, out_path, timestamp):
        with closing(ZipFile(out_path, "w")) as out_zip:
            # write the backup manifest
            out_zip.writestr("manifest.json", json.dumps(dict(
                version=minv.__version__,
                timestamp=timestamp,
                logs=self.logs,
                config=self.config,
                app=self.app,
                **self.get_manifest()
            )))

            if self.logs:
                for path in glob.glob("/var/log/minv/minv.log*"):
                    self.backup_file(path, "logs/%s" % basename(path), out_zip)
            if self.config:
                self.backup_file(
                    "/etc/minv/minv.conf", "config/minv.conf", out_zip
                )

                for collection in models.Collection.objects.all():
                    # backup the configuration
                    self.backup_file(
                        collection.config_path,
                        "config/collections/%s/collection.conf" % collection,
                        out_zip
                    )
                    # backup the locations
                    out_zip.writestr(
                        "config/collections/%s/locations.json" % collection,
                        json.dumps([
                            {
                                "url": location.url,
                                "location_type": location.location_type
                            }
                            for location in collection.locations.all()
                        ])
                    )
            if self.app:
                # TODO: decide.
                pass


class IncrementalBackup(FullBackup):
    """ Class for incremental backups. In difference to full backups, this class
    only selects files that are younger than the given timestamp.
    """
    def __init__(self, logs, config, app, incr):
        super(IncrementalBackup, self).__init__(logs, config, app)
        try:
            duration = parse_duration(incr)
            self.timestamp = (now() - duration).timestamp()
        except ValueError:
            self.timestamp = parse(incr).timestamp()

        self.timestamp = incr

    def decide_file(self, path, zip_path):
        return getmtime(path) > self.timestamp

    def get_manifest(self):
        return {"type": "incremental"}


class DifferentialBackup(FullBackup):
    """ Class for differential backups. In difference to full backups, this class
    only selects files that are not within or older than the file of the
    specified backup.
    """
    def __init__(self, logs, config, app, diff):
        super(DifferentialBackup, self).__init__(logs, config, app)
        self.diff_zip = None
        self.diff_path = diff

    def perform(self, out_path, timestamp):
        with closing(ZipFile(self.diff_path)) as diff_zip:
            self.diff_zip = diff_zip
            super(DifferentialBackup, self).perform(out_path, timestamp)
            self.diff_zip = None

    def decide_file(self, path, zip_path):
        try:
            info = self.diff_zip.getinfo(zip_path)
            datetime(*info.date_time) < datetime.fromtimestamp(getmtime(path))
        except KeyError:
            return True

    def get_manifest(self):
        return {"type": "differential"}
