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
from os.path import join, basename
import zipfile
import json
from contextlib import closing
import tempfile
import csv
from shutil import rmtree, move
import logging

from django.utils.timezone import now
from django.db import transaction

import minv
from minv.inventory import models
from minv.inventory.ingest import ingest
from minv.utils import safe_makedirs
from minv.tasks.registry import task
from minv.tasks.api import schedule


logger = logging.getLogger(__name__)


class ImportException(Exception):
    pass


@task("export")
def export_collection(mission, file_type, filename=None,
                      configuration=True, data=True, reschedule=False):
    """ Export the configuration and/or the data of a collection to a ZIP file.
    """

    collection = models.Collection.objects.get(
        mission=mission, file_type=file_type
    )

    if not configuration and not data:
        raise RuntimeError("Neither collection nor data export specified")

    # create a default filename if none was specified
    if not filename:
        exports_dir = join(collection.data_dir, "exports")
        safe_makedirs(exports_dir)
        new_filename = join(
            exports_dir, "export_%s.zip" % now().strftime("%Y%m%d-%H%M%S")
        )

    with collection.get_lock():
        ret_val = _export_collection_locked(
            collection, filename or new_filename, configuration, data
        )

        logger.info(
            "Successfully exported %s collection to %s" % (collection, filename)
        )

        if reschedule:
            try:
                interval = collection.configuration.export_interval
                schedule("export", now() + interval, {
                    "mission": mission,
                    "file_type": file_type,
                    "filename": filename,
                    "configuration": configuration,
                    "data": data,
                    "reschedule": True
                })
            except Exception as exc:
                logger.error(
                    "Failed to reschedule export for %s. Error was '%s'." % (
                        collection, exc
                    )
                )

        return ret_val


def _export_collection_locked(collection, filename, configuration, data):
    # create the ZIP archive
    with closing(zipfile.ZipFile(filename, "w")) as archive:
        # write a manifest to set the version of the exported software
        archive.writestr("manifest.json", json.dumps({
            "version": minv.__version__,
            "mission": collection.mission,
            "file_type": collection.file_type
        }))

        # export the configuration when required
        if configuration:
            archive.write(
                join(collection.config_dir, "collection.conf"), "collection.conf"
            )

        # write location info
        archive.writestr("locations.json", json.dumps(
            dict(
                (location.url, {
                    "type": location.location_type,
                    "directory": location.slug
                })
                for location in collection.locations.all()
            )
        ))

        # export data when required
        if data:
            for location in collection.locations.all():
                ingested_dir = join(
                    collection.data_dir, "ingested", location.slug
                )
                for index_file in location.index_files.all():
                    arcname = join(
                        "locations", location.slug, basename(index_file.filename)
                    )
                    archive.write(
                        join(ingested_dir, index_file.filename),
                        arcname=arcname
                    )

                with tempfile.NamedTemporaryFile() as tmp_file:
                    writer = csv.writer(tmp_file)
                    writer.writerow(["filename", "text"])
                    annotations_qs = models.Annotation.objects.filter(
                        record__location=location
                    ).values_list("record__filename", "text")
                    for record_filename, text in annotations_qs:
                        writer.writerow([record_filename, text])

                    tmp_file.flush()

                    archive.write(
                        tmp_file.name, arcname=join(
                            "locations", location.slug, "annotations.csv"
                        )
                    )

    os.chmod(filename, 0660)

    return filename


@task("import")
@transaction.atomic
def import_collection(filename, mission=None, file_type=None):
    """ Import a previously exported archive.
    """
    collections_qs = models.Collection.objects.filter(
        mission=mission, file_type=file_type
    )
    if collections_qs.exists():
        raise ImportException("Collection %s/%s already exists." % (
            mission, file_type
        ))

    if not zipfile.is_zipfile(filename):
        raise ImportException("File %s is not a ZIP file." % filename)

    with closing(zipfile.ZipFile(filename, "r")) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        # TODO: better version check

        mission = mission or manifest["mission"]
        file_type = file_type or manifest["file_type"]

        collection = models.Collection.objects.create(
            mission=mission, file_type=file_type
        )

        if minv.__version__ != manifest["version"]:
            raise ImportException(
                "Cannot import file %s due to version mismatch: %r != %r"
                % (filename, minv.__version__, manifest["version"])
            )

        locations = json.loads(archive.read("locations.json"))

        for url, values in locations.items():
            models.Location.objects.create(
                collection=collection, url=url, location_type=values["type"]
            )

        try:
            archive.extract("collection.conf", collection.config_dir)
        except KeyError:
            pass

        slug_to_location = dict(
            (location.slug, location)
            for location in collection.locations.all()
        )

        # create a temporary directory tree to extract files to
        tmp_dir = tempfile.mkdtemp()

        # extract index files and ingest them
        members = [
            member for member in archive.namelist()
            if member.startswith("locations/") and
            basename(member) != "annotations.csv"
        ]
        try:
            for member in members:
                slug, _, index_filename = member[10:].partition("/")
                url = slug_to_location[slug].url

                directory = join(collection.data_dir, "pending", slug)
                safe_makedirs(directory)

                path = archive.extract(member, tmp_dir)
                move(path, directory)
                ingest(mission, file_type, url, index_filename)
        finally:
            rmtree(tmp_dir)

        # read annotations
        members = [
            member for member in archive.namelist()
            if member.startswith("locations/") and
            member.endswith("annotations.csv")
        ]
        for member in members:
            slug, _, index_filename = member[10:].partition("/")
            location = slug_to_location[slug]
            with closing(archive.open(member)) as annotations:
                reader = csv.reader(annotations)
                next(reader)  # skip header
                for record_filename, text in reader:
                    models.Annotation.objects.create(
                        record=models.Record.objects.get(
                            location=location, filename=record_filename
                        ),
                        text=text
                    )

    return collection


def list_exports(mission, file_type):
    """ List the available exports for a collection.
    """
    collection = models.Collection.objects.get(
        mission=mission, file_type=file_type
    )
    try:
        return os.listdir(join(collection.data_dir, "exports"))
    except OSError:
        return []
