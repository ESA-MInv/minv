from django.contrib import admin

import models


class LocationInline(admin.StackedInline):
    extra = 0
    model = models.Location


@admin.register(models.MissionAndType)
class MissionAndTypeAdmin(admin.ModelAdmin):
    inlines = (LocationInline,)
    verbose_name = "Mission and Type"


@admin.register(models.Location)
class LocationAdmin(admin.ModelAdmin):
    pass


@admin.register(models.IndexFile)
class IndexFileAdmin(admin.ModelAdmin):
    pass


class AnnotationInline(admin.StackedInline):
    extra = 1
    model = models.Annotation


@admin.register(models.Record)
class RecordAdmin(admin.ModelAdmin):
    inlines = (AnnotationInline,)
