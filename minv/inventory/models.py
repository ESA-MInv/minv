from os import makedirs, rmdir
from os.path import join, exists
import json

from django.contrib.gis.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings


SEARCH_FIELD_CHOICES = (
    ("filename", "File Name"),
    ("filesize", "File Size"),
    ("orbit_number", "Orbit Number"),
    ("track", "Track"),
    ("frame", "Frame"),
    ("platform_serial_identifier", "Platform Serial Identifier"),
    ("mission_phase", "Mission Phase"),
    ("operational_mode", "Operational Mode"),
    ("swath", "Swath"),
    ("instrument", "Instrument"),
    ("product_id", "Product ID"),
    ("begin_time", "Begin Acquisistion"),
    ("end_time", "End Acquisition"),
    ("insertion_time", "Insertion Time"),
    ("creation_date", "Creation Time"),
    ("baseline", "Baseline/Version"),
    ("processing_centre", "Processing Centre"),
    ("processing_date", "Processing Date"),
    ("processing_mode", "Processing Mode"),
    ("processor_version", "Processor Version"),
    ("acquisition_station", "Acquisition Station"),
    ("orbit_direction", "Orbit Direction"),
    ("product_quality_degradatation", "Product Quality Degradation"),
    ("product_quality_status", "Product Quality Status"),
    ("product_quality_degradatation_tag", "Product Quality Degredation Tag")
)


class Collection(models.Model):
    mission = models.CharField(max_length=512)
    file_type = models.CharField(max_length=512)

    def __unicode__(self):
        return "%s/%s" % (self.mission, self.file_type)

    def get_metadata_field_mapping(self):
        with open(join(self.config_dir, "mapping.json")) as f:
            return json.load(f)
        # return dict(
        #     (mapping.indexfile_key, mapping.search_key)
        #     for mapping in self.metadata_field_mappings.all()
        # )

    @property
    def config_dir(self):
        return join(
            settings.MINV_CONFIG_DIR, "collections",
            self.mission, self.file_type
        )

    @property
    def data_dir(self):
        return join(
            settings.MINV_DATA_DIR, "collections", self.mission, self.file_type
        )

    class Meta:
        unique_together = (("mission", "file_type"),)


# TODO: maybe put this into a configfile per collection
class MetadataFieldMapping(models.Model):
    collection = models.ForeignKey("Collection",
                                   related_name="metadata_field_mappings")
    indexfile_key = models.CharField(max_length=256)
    search_key = models.CharField(max_length=256, choices=SEARCH_FIELD_CHOICES)

    def __unicode__(self):
        return "%s -> %s" % (self.indexfile_key, self.search_key)

    class Meta:
        unique_together = (("collection", "search_key"),)


class Location(models.Model):
    collection = models.ForeignKey("Collection", related_name="locations")
    url = models.URLField()
    location_type = models.CharField(max_length=4,
                                     choices=(("oads", "OADS"), ("nga", "ngA")))

    class Meta:
        unique_together = (("collection", "url"),)

    def __unicode__(self):
        return "%s (%s)" % (self.url, self.get_location_type_display())


class IndexFile(models.Model):
    location = models.ForeignKey("Location", related_name="index_files")
    filename = models.CharField(max_length=512)
    begin_time = models.DateTimeField()
    end_time = models.DateTimeField()
    update_time = models.DateTimeField()
    insertion_time = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return "%s (%s)" % (self.filename, self.location)


class Record(models.Model):
    location = models.ForeignKey("Location")
    index_file = models.ForeignKey("IndexFile")
    filename = models.CharField(max_length=256, db_index=True)
    filesize = models.IntegerField()
    checksum = models.CharField(max_length=256, null=True, blank=True)

    # TODO: "row" or "offset" in file

    # query fields
    # TODO: region = # TODO
    orbit_number = models.IntegerField(null=True, blank=True, db_index=True)
    track = models.IntegerField(null=True, blank=True, db_index=True)
    frame = models.IntegerField(null=True, blank=True, db_index=True)
    platform_serial_identifier = models.CharField(max_length=256, null=True,
                                                  blank=True, db_index=True)
    mission_phase = models.CharField(max_length=256, null=True, blank=True,
                                     db_index=True)
    operational_mode = models.CharField(max_length=64, null=True, blank=True,
                                        db_index=True)
    swath = models.IntegerField(null=True, blank=True, db_index=True)
    instrument = models.CharField(max_length=256, null=True, blank=True,
                                  db_index=True)
    product_id = models.CharField(max_length=1024, null=True, blank=True,
                                  db_index=True)

    # TODO: file class / originator
    begin_time = models.DateTimeField(null=True, blank=True, db_index=True)
    end_time = models.DateTimeField(null=True, blank=True, db_index=True)
    insertion_time = models.DateTimeField(null=True, blank=True, db_index=True)
    creation_date = models.DateTimeField(null=True, blank=True, db_index=True)
    baseline = models.CharField(max_length=256, null=True, blank=True,
                                db_index=True)

    scene_centre = models.PointField(null=True, blank=True, db_index=True)
    footprint = models.MultiPolygonField(null=True, blank=True, db_index=True)

    processing_centre = models.CharField(max_length=256, null=True, blank=True,
                                         db_index=True)
    processing_date = models.DateTimeField(null=True, blank=True, db_index=True)
    processing_mode = models.CharField(max_length=64, null=True, blank=True,
                                       db_index=True)
    processor_version = models.CharField(max_length=32, null=True, blank=True,
                                         db_index=True)
    acquisition_station = models.CharField(max_length=256, null=True, blank=True,
                                           db_index=True)
    orbit_direction = models.CharField(max_length=1, null=True, blank=True,
                                       db_index=True,
                                       choices=(("A", "ASCENDING"),
                                                ("D", "DESCENDING")))
    product_quality_degradatation = models.FloatField(null=True, blank=True,
                                                      db_index=True)
    product_quality_status = models.CharField(max_length=1, null=True,
                                              blank=True, db_index=True,
                                              choices=(("N", "NOMINAL"),
                                                       ("D", "DEGRADED")))
    product_quality_degradatation_tag = models.CharField(max_length=4096,
                                                         null=True, blank=True,
                                                         db_index=True)

    objects = models.GeoManager()

    class Meta:
        unique_together = (("filename", "location"),)

    def __unicode__(self):
        return "%s (%s)" % (self.filename, self.location)


class Annotation(models.Model):
    record = models.ForeignKey("Record", related_name="annotations")
    text = models.TextField()
    insertion_time = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return self.text

# setup and teardown stuff


@receiver(post_save)
def on_collection_created(sender, instance, created, **kwargs):
    if sender is Collection and created:
        try:
            makedirs(instance.config_dir)
        except OSError:
            pass
        if not exists(join(instance.config_dir, "mapping.json")):
            with open(join(instance.config_dir, "mapping.json"), "w") as f:
                json.dump({}, f)

        if not exists(join(instance.config_dir, "collection.conf")):
            with open(join(instance.config_dir, "collection.conf"), "w") as f:
                f.write("[inventory]")
                # TODO: default values for configuration
        try:
            makedirs(instance.data_dir)
        except OSError:
            pass


@receiver(post_delete)
def on_collection_deleted(sender, instance, **kwargs):
    if sender is Collection:
        rmdir(instance.data_dir)
        # if that was the only collection with that exact mission, remove the
        # mission dir aswell
        if not Collection.objects.filter(mission=instance.mission).exists():
            rmdir(join(settings.MINV_DATA_DIR, "collections", instance.mission))
