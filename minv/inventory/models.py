from os import rmdir
from shutil import rmtree
from os.path import join, exists

from django.contrib.gis.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings
from django.utils.text import slugify

from minv.inventory.collection import config
from minv.utils import safe_makedirs


SEARCH_FIELD_CHOICES = (
    ("filename", "File Name"),
    ("filesize", "File Size"),
    ("checksum", "Checksum"),
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
    ("file_type", "File Type/Originator"),
    ("product_quality_degradatation", "Product Quality Degradation"),
    ("product_quality_status", "Product Quality Status"),
    ("product_quality_degradatation_tag", "Product Quality Degredation Tag"),
    ("footprint", "Footprint"),
    ("scene_centre", "Scene Centre"),
)

ALIGNMENT_FIELD_CHOICES = (
    ("orbit_number", "Orbit Number"),
    ("track", "Track"),
    ("frame", "Frame"),
    ("platform_serial_identifier", "Platform Serial Identifier"),
    ("instrument", "Instrument"),
    ("creation_date", "Creation Time"),
    ("baseline", "Baseline/Version"),
)


class Collection(models.Model):
    mission = models.CharField(max_length=512)
    file_type = models.CharField(max_length=512)

    def __unicode__(self):
        return "%s/%s" % (self.mission, self.file_type)

    def get_metadata_field_mapping(self):
        return self.configuration.metadata_mapping

    @property
    def config_dir(self):
        return join(
            settings.MINV_CONFIG_DIR, "collections",
            self.mission, self.file_type
        )

    @property
    def configuration(self):
        return config.CollectionConfigurationReader(
            join(self.config_dir, "collection.conf")
        )

    @property
    def data_dir(self):
        return join(
            settings.MINV_DATA_DIR, "collections", self.mission, self.file_type
        )

    class Meta:
        unique_together = (("mission", "file_type"),)
        permissions = (
            ("can_configure_collections", "Can configure collections"),
            ("can_export", "Can export a collection"),
            ("can_backup", "Can backup the application"),
        )


class Location(models.Model):
    collection = models.ForeignKey("Collection", related_name="locations")
    url = models.URLField()
    location_type = models.CharField(max_length=4,
                                     choices=(("oads", "OADS"), ("nga", "ngA")))

    class Meta:
        unique_together = (("collection", "url"),)

    def __unicode__(self):
        return "%s (%s)" % (self.url, self.get_location_type_display())

    @property
    def slug(self):
        return slugify(unicode(self.url))


class IndexFile(models.Model):
    location = models.ForeignKey("Location", related_name="index_files")
    filename = models.CharField(max_length=512)
    begin_time = models.DateTimeField()
    end_time = models.DateTimeField()
    update_time = models.DateTimeField()
    insertion_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("filename", "location"),)

    def __unicode__(self):
        return "%s (%s)" % (self.filename, self.location)


optional = dict(null=True, blank=True, db_index=True)


class Record(models.Model):
    location = models.ForeignKey("Location", related_name="records")
    index_file = models.ForeignKey("IndexFile")
    filename = models.CharField(max_length=256, db_index=True)
    filesize = models.IntegerField()
    checksum = models.CharField(max_length=256)

    # TODO: "row" or "offset" in file

    orbit_number = models.IntegerField(**optional)
    track = models.IntegerField(**optional)
    frame = models.IntegerField(**optional)
    platform_serial_identifier = models.CharField(max_length=256, **optional)
    mission_phase = models.CharField(max_length=256, **optional)
    operational_mode = models.CharField(max_length=64, **optional)
    swath = models.IntegerField(**optional)
    instrument = models.CharField(max_length=256, **optional)
    product_id = models.CharField(max_length=1024, **optional)
    begin_time = models.DateTimeField(**optional)
    end_time = models.DateTimeField(**optional)
    insertion_time = models.DateTimeField(**optional)
    creation_date = models.DateTimeField(**optional)
    baseline = models.CharField(max_length=256, **optional)
    scene_centre = models.PointField(**optional)
    footprint = models.MultiPolygonField(**optional)
    processing_centre = models.CharField(max_length=256, **optional)
    processing_date = models.DateTimeField(**optional)
    processing_mode = models.CharField(max_length=64, **optional)
    processor_version = models.CharField(max_length=32, **optional)
    acquisition_station = models.CharField(max_length=256, **optional)
    orbit_direction = models.CharField(
        max_length=1, choices=(("A", "ASCENDING"), ("D", "DESCENDING")),
        **optional
    )
    file_type = models.CharField(max_length=16, **optional)
    product_quality_degradatation = models.FloatField(**optional)
    product_quality_status = models.CharField(
        max_length=1, choices=(("N", "NOMINAL"), ("D", "DEGRADED")), **optional
    )
    product_quality_degradatation_tag = models.CharField(
        max_length=4096, **optional
    )

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
        safe_makedirs(instance.config_dir)

        if not exists(join(instance.config_dir, "collection.conf")):
            with open(join(instance.config_dir, "collection.conf"), "w") as f:
                f.write("[inventory]")
                # TODO: default values for configuration

        safe_makedirs(instance.data_dir)


@receiver(post_delete)
def on_collection_deleted(sender, instance, **kwargs):
    if sender is Collection:
        rmtree(instance.data_dir)
        # if that was the only collection with that exact mission, remove the
        # mission dir aswell
        if not Collection.objects.filter(mission=instance.mission).exists():
            rmdir(join(settings.MINV_DATA_DIR, "collections", instance.mission))
