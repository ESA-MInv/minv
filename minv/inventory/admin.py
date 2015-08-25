from django.contrib import admin

import models


class MetadataFieldMappingInline(admin.TabularInline):
    extra = 0
    model = models.MetadataFieldMapping


class LocationInline(admin.TabularInline):
    extra = 0
    model = models.Location


def location_count(collection):
    return collection.locations.all().count()


def index_file_count(collection):
    return models.IndexFile.objects.filter(
        location__collection=collection).count()


def record_count(collection):
    return models.Record.objects.filter(location__collection=collection).count()


@admin.register(models.Collection)
class CollectionAdmin(admin.ModelAdmin):
    inlines = (LocationInline, MetadataFieldMappingInline)
    list_display = (
        "mission", "file_type", location_count, index_file_count, record_count
    )
    list_display_links = ("mission", "file_type")


@admin.register(models.IndexFile)
class IndexFileAdmin(admin.ModelAdmin):
    pass


class AnnotationInline(admin.TabularInline):
    extra = 1
    model = models.Annotation


@admin.register(models.Record)
class RecordAdmin(admin.ModelAdmin):
    inlines = (AnnotationInline,)
