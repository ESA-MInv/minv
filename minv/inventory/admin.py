from django.contrib import admin

from minv.inventory import models


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


class CollectionAdmin(admin.ModelAdmin):
    inlines = (LocationInline,)
    list_display = (
        "mission", "file_type", location_count, index_file_count, record_count
    )
    list_display_links = ("mission", "file_type")

admin.site.register(models.Collection, CollectionAdmin)


class IndexFileAdmin(admin.ModelAdmin):
    pass

admin.site.register(models.IndexFile, IndexFileAdmin)


class AnnotationInline(admin.TabularInline):
    extra = 1
    model = models.Annotation


class RecordAdmin(admin.ModelAdmin):
    inlines = (AnnotationInline,)

admin.site.register(models.Record, RecordAdmin)
