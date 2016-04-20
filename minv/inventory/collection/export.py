from os import makedirs, listdir
from os.path import join, basename
import zipfile
import json
from contextlib import closing
import tempfile
import csv

from django.utils.timezone import now
from django.db import transaction

import minv
from minv.inventory import models
from minv.inventory.ingest import ingest


class ImportException(Exception):
    pass


def export_collection(mission, file_type, filename=None,
                      configuration=True, data=True):
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
        try:
            makedirs(exports_dir)
        except OSError:
            pass
        filename = join(
            exports_dir, "export_%s.zip" % now().strftime("%Y%m%d-%H%M%S")
        )

    # create the ZIP archive
    with closing(zipfile.ZipFile(filename, "w")) as archive:
        # write a manifest to set the version of the exported software
        archive.writestr("manifest.json", json.dumps({
            "version": minv.__version__,
            "mission": mission,
            "file_type": file_type
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

    return filename


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

        print slug_to_location

        # extract index files and ingest them
        members = [
            member for member in archive.namelist()
            if member.startswith("locations/") and
            basename(member) != "annotations.csv"
        ]
        for member in members:
            print member, member [10:]
            slug, _, index_filename = member[10:].partition("/")
            url = slug_to_location[slug].url

            directory = join(collection.data_dir, "pending", slug)
            archive.extract(member, directory)
            ingest(
                mission, file_type, url, join(directory, index_filename)
            )

        # read annotations
        members = [
            member for member in archive.namelist()
            if member.startswith("locations/") and
            member.endswith("annotations.csv")
        ]
        for member in members:
            slug, _, index_filename = member[9:].partition("/")
            location = slug_to_location[slug]
            with archive.open(member) as annotations:
                reader = csv.reader(annotations)
                next(reader)  # skip header
                for record_filename, text in reader:
                    models.Annotation.objects.create(
                        record=models.Record.objects.get(
                            location=location, filename=record_filename
                        )
                    )

    return collection


def list_exports(mission, file_type):
    """ List the available exports for a collection.
    """
    collection = models.Collection.objects.get(
        mission=mission, file_type=file_type
    )
    try:
        return listdir(join(collection.data_dir, "exports"))
    except OSError:
        return []
