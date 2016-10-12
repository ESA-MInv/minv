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
