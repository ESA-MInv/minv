from os import makedirs, listdir
from os.path import join, basename
import zipfile
import json
from contextlib import closing

from django.utils.timezone import now

from minv.inventory import models


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
        if configuration:
            archive.write(
                join(collection.config_dir, "collection.conf"), "collection.conf"
            )

        # write location info
        archive.writestr("locations/locations.json", json.dumps(
            dict(
                (location.url, {
                    "type": location.location_type,
                    "directory": location.slug
                })
                for location in collection.locations.all()
            )
        ))

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

    return filename


def import_collection(mission, file_type, filename,
                      configuration=True, data=True):
    """ Import a previously exported archive.
    """
    collection, created = models.Collection.objects.get_or_create(
        mission=mission, file_type=file_type
    )
    if created:
        print "Created collection %s" % collection


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
