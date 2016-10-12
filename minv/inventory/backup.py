# ------------------------------------------------------------------------------
#
# Project: Master Inventory <http://github.com/ESA-MInv/minv>
# Authors: Fabian Schindler <fabian.schindler@eox.at>
#
# ------------------------------------------------------------------------------
# Copyright (C) 2016 European Space Agency
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies of this Software or works derived from this Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
# ------------------------------------------------------------------------------


import os
from os.path import join, basename, getmtime, exists, isfile
import sys
from zipfile import ZipFile
import glob
from contextlib import closing
from datetime import datetime
import json
import shutil
import logging

from django.utils.timezone import now
from django.utils.dateparse import parse_datetime

import minv
from minv.inventory import models
from minv.tasks.registry import task
from minv.utils import safe_makedirs, parse_duration, timestamp
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


def get_available_backups():
    print os.listdir(BASE_PATH)
    return [
        (path, "incremental" if "incr" in path else
            "differential" if "diff" in path else "full")
        for path in os.listdir(BASE_PATH)
        if isfile(join(BASE_PATH, path))
    ]


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
            "Differential and incremental backups are mutually exclusive."
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
        os.chmod(out_path, 0660)
    except Exception:
        exc_info = sys.exc_info()
        try:
            os.unlink(out_path)
        except OSError:
            pass
        raise exc_info[0], exc_info[1], exc_info[2]

    return out_path


def restore(in_path):
    """ Restore a previously backupped ZIP.
    """
    with closing(ZipFile(in_path)) as in_zip:
        manifest = json.loads(in_zip.read("manifest.json"))
        names = in_zip.namelist()

        if manifest["logs"]:
            # restore logs
            for name in names:
                extract = False
                # extract the file if it does not exist in the filesystem, or the
                # filesystem version is older
                if name.startswith("logs/"):
                    if exists(join("/var/log/minv", basename(name))):
                        ts = timestamp(datetime(*in_zip.getinfo(name).date_time))
                        if ts > getmtime(join("/var/log/minv", basename(name))):
                            extract = True
                    else:
                        extract = True

                if extract:
                    _restore_file(
                        in_zip, name, join("/var/log/minv", basename(name))
                    )

        if manifest["config"]:
            # restore the global configuration
            errors = check_global_configuration(
                GlobalReader.from_fileobject(in_zip.open("config/minv.conf"))
            )
            if not errors:
                backup_config("/etc/minv/minv.conf")
                _restore_file(in_zip, "config/minv.conf", "/etc/minv/minv.conf")
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
        _restore_file(in_zip, zip_config_path, collection.config_path)
        logger.info("Restored configuration for collection %s" % collection)
    else:
        logger.warn(
            "Could not restore collection configuration due to errors:\n%s"
            % ("\n".join(errors))
        )


def _restore_file(in_zip, name, path):
    """ Utility function to restore a single file from a zip to a given path.
    """
    with open(path, "w") as f:
        shutil.copyfileobj(in_zip.open(name), f)


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
            self.timestamp = timestamp(now() - duration)
        except ValueError:
            self.timestamp = timestamp(parse_datetime(incr))

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
