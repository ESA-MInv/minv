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


from functools import wraps
import tempfile
import csv
from os.path import basename, join

from django.shortcuts import render
from django.core.paginator import Paginator
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.datastructures import SortedDict
from django.utils.timezone import now
from django.http import StreamingHttpResponse, Http404
from django.db.models import Sum, Count
from django.contrib.auth.decorators import permission_required, login_required

from minv.config import backup_config
from minv.inventory import models
from minv.inventory import forms
from minv.inventory import queries
from minv.inventory.collection.export import (
    export_collection, list_exports
)
from minv.inventory.collection.config import check_collection_configuration
from minv.utils import get_or_none, timedelta_to_duration
from minv.tasks.api import monitor, schedule_many


def check_collection(view):
    """ Decorator to check whether a collection exists or not.
    """
    @wraps(view)
    def wrapped(request, mission, file_type, *args, **kwargs):
        try:
            return view(request, mission, file_type, *args, **kwargs)
        except models.Collection.DoesNotExist:
            return render(
                request, "inventory/collection/404.html", {
                    "collections": models.Collection.objects.all(),
                    "mission": mission, "file_type": file_type
                }
            )
    return wrapped


@login_required(login_url="login")
def list_view(request):
    """ Django view function to show a list of registered collections.
    """
    return render(
        request, "inventory/collection/list.html", {
            "collections": models.Collection.objects.all()
        }
    )


@login_required(login_url="login")
@check_collection
def detail_view(request, mission, file_type):
    """ Django view function to show the collections dashboard page.
    """
    collection = models.Collection.objects.get(
        mission=mission, file_type=file_type
    )
    return render(
        request, "inventory/collection/detail.html", {
            "collections": models.Collection.objects.all(),
            "collection": collection
        }
    )


@login_required(login_url="login")
@check_collection
def harvest_view(request, mission, file_type):
    """ Django view function to inspect ongoing harvests and trigger new ones.
    """
    collection = models.Collection.objects.get(
        mission=mission, file_type=file_type
    )

    items = []
    for url in request.GET.getlist("url"):
        messages.info(request, "Harvesting URL %s for collection %s" % (
            url, collection
        ))
        items.append(("harvest", now(), {
            "mission": mission,
            "file_type": file_type,
            "url": url,
            "reschedule": False
        }))

    schedule_many(items)

    return redirect("inventory:collection:detail",
        mission=mission, file_type=file_type
    )


def get_available_search_fields(collection):
    available_search_fields = set()
    for location in collection.locations.all():
        available_search_fields |= set(
            collection.get_metadata_field_mapping(
                location.url
            ).keys()
        )
    return available_search_fields


@login_required(login_url="login")
@check_collection
def search_view(request, mission, file_type):
    """ Django view function to perform the collection search.
    """
    collection = models.Collection.objects.get(
        mission=mission, file_type=file_type
    )

    available_search_fields = get_available_search_fields(collection)

    results = None
    if request.method == "POST":
        search_form = forms.SearchForm(
            collection.locations.all(), available_search_fields, request.POST
        )
        pagination_form = forms.PaginationForm(request.POST)
        result_list_form = forms.RecordSearchResultListForm(
            collection.locations.all(), request.POST
        )
        forms_valid = (
            search_form.is_valid() and pagination_form.is_valid() and
            result_list_form.is_valid()
        )
        if forms_valid:
            search_data = search_form.cleaned_data
            location_ids = search_data.pop("locations", ())

            # TODO: only scene centre??
            footprint_or_scene_centre = search_data.pop(
                "area_footprint_or_scene_centre", "footprint"
            )

            if location_ids:
                locations = collection.locations.filter(id__in=location_ids)
            else:
                locations = collection.locations.all()

            observer = monitor(
                "search_overview", **search_data
            )
            with observer:
                results = []
                for location in locations:
                    qs = queries.search(
                        collection, search_data, location.records.all(),
                        footprint_or_scene_centre == "footprint"
                    )
                    values = qs.aggregate(
                        volume=Sum("filesize"), count=Count("filename")
                    )
                    results.append((location, values))

    else:
        search_form = forms.SearchForm(
            collection.locations.all(), available_search_fields
        )
        pagination_form = forms.PaginationForm(
            initial={'page': '1', 'records_per_page': '15'}
        )
        result_list_form = forms.RecordSearchResultListForm(
            collection.locations.all()
        )

    return render(
        request, "inventory/collection/search.html", {
            "collections": models.Collection.objects.all(),
            "search_form": search_form,
            "pagination_form": pagination_form,
            "result_list_form": result_list_form,
            "collection": collection, "results": results
        }
    )


@login_required(login_url="login")
@check_collection
def result_list_view(request, mission, file_type):
    """
    """
    collection = models.Collection.objects.get(
        mission=mission, file_type=file_type
    )
    location = None

    available_search_fields = get_available_search_fields(collection)

    config = collection.configuration
    all_choices = dict((("checksum", "Checksum"),) + models.SEARCH_FIELD_CHOICES)

    display_fields = SortedDict(
        (field_id, all_choices[field_id])
        for field_id in config.available_result_list_fields or []
    )

    results = None
    result_list = None
    result_list_location = None
    if request.method == "POST":
        search_form = search_form = forms.SearchForm(
            collection.locations.all(), available_search_fields, request.POST
        )
        pagination_form = forms.PaginationForm(request.POST)
        result_list_form = forms.RecordSearchResultListForm(
            collection.locations.all(), request.POST
        )

        forms_valid = (
            search_form.is_valid() and pagination_form.is_valid() and
            result_list_form.is_valid()
        )

        if forms_valid:
            search_data = search_form.cleaned_data
            result_list_location_id = result_list_form.cleaned_data[
                "result_list_location"
            ]

            # TODO: only scene centre??
            footprint_or_scene_centre = search_data.pop(
                "area_footprint_or_scene_centre", "footprint"
            )

            location = collection.locations.get(id=result_list_location_id)

            observer = monitor(
                "search_results", **search_data
            )
            with observer:
                qs = queries.search(
                    collection, search_data, location.records.all(),
                    footprint_or_scene_centre == "footprint"
                )

            sort = result_list_form.cleaned_data.pop("sort", None)
            if sort:
                qs = qs.order_by(sort)

            page = pagination_form.cleaned_data.pop("page")
            per_page = pagination_form.cleaned_data.pop(
                "records_per_page"
            )

            result_list = Paginator(qs, per_page).page(page)
            result_list_location = location

            # see if we need to create annotations
            add_annotation_list_form = forms.AddAnnotationListForm(request.POST)
            if add_annotation_list_form.is_valid() and \
                    add_annotation_list_form.cleaned_data["text"] and \
                    add_annotation_list_form.cleaned_data["do_add_annotation"]:

                ids = map(int, request.POST.getlist(
                    "add_record_annotation", []
                ))

                if add_annotation_list_form.cleaned_data[
                        "add_annotations_to_all"]:
                    annotation_qs = qs
                else:
                    annotation_qs = location.records.filter(pk__in=ids)

                for record in annotation_qs:
                    models.Annotation.objects.create(
                        record=record,
                        text=add_annotation_list_form.cleaned_data["text"]
                    )

    else:
        search_form = forms.SearchForm(
            collection.locations.all(), available_search_fields
        )
        pagination_form = forms.PaginationForm(
            initial={'page': '1', 'records_per_page': '15'}
        )
        result_list_form = forms.RecordSearchResultListForm(
            collection.locations.all()
        )

    # Response formats

    if request.POST.get("download_csv"):
        keys = display_fields.keys()
        f = tempfile.SpooledTemporaryFile()
        writer = csv.writer(f, delimiter=",")
        writer.writerow(
            ["filename"] + keys
        )
        for record in qs:
            writer.writerow([
                record.filename
            ] + [
                getattr(record, key, "")
                for key in keys
            ])

        size = f.tell()
        f.seek(0)

        response = StreamingHttpResponse(f, content_type="text/csv")
        response["Content-Length"] = str(size)
        response["Content-Disposition"] = (
            'inline; filename="search-%s.csv"' % (
                now().replace(microsecond=0, tzinfo=None).isoformat("T")
            )
        )
        return response

    elif request.POST.get("download_filenames"):
        f = tempfile.SpooledTemporaryFile()
        for record in qs:
            f.write(record.filename)
            f.write("\n")

        size = f.tell()
        f.seek(0)

        response = StreamingHttpResponse(f, content_type="text/plain")
        response["Content-Length"] = str(size)
        response["Content-Disposition"] = (
            'inline; filename="search-%s.txt"' % (
                now().replace(microsecond=0, tzinfo=None).isoformat("T")
            )
        )
        return response

    else:
        # overwrite on purpose
        add_annotation_list_form = forms.AddAnnotationListForm()
        return render(
            request, "inventory/collection/result_list.html", {
                "collections": models.Collection.objects.all(),
                "search_form": search_form,
                "pagination_form": pagination_form,
                "result_list_form": result_list_form,
                "add_annotation_list_form": add_annotation_list_form,
                "collection": collection,
                "location": location,
                "results": results,
                "result_list": result_list,
                "result_list_location": result_list_location,
                "metadata_fields": display_fields
            }
        )


@login_required(login_url="login")
@check_collection
def record_view(request, mission, file_type, filename):
    """ Django view function to inspect a specific record specified by its
    filename.
    """
    collection = models.Collection.objects.get(
        mission=mission, file_type=file_type
    )
    records = models.Record.objects.filter(
        filename=filename, location__collection=collection
    )
    display_fields = SortedDict(
        (("checksum", "Checksum"),) + models.SEARCH_FIELD_CHOICES
    )
    locations = SortedDict((
        (location, get_or_none(records, location=location))
        for location in collection.locations.all()
    ))

    reference_record, others = records[0], records[1:]
    differences = set()
    for field in display_fields.keys():
        for record in others:
            if getattr(record, field) != getattr(reference_record, field):
                differences.add(field)

    distinct_checksums = set([
        record.checksum for record in records
        if record.checksum is not None
    ])
    checksum_mismatch = False

    if len(distinct_checksums) > 1:
        checksum_mismatch = True

    # TODO: make this in annotation_view
    if request.method == "POST":
        add_annotation_form = forms.AddAnnotationForm(
            [record.location for record in records], request.POST
        )
        if add_annotation_form.is_valid():
            data = add_annotation_form.cleaned_data
            annotation_records = [
                models.Record.objects.get(
                    filename=filename, location=data["location"]
                )
            ] if data["location"] else records
            for record in annotation_records:
                models.Annotation.objects.create(
                    record=record, text=data["text"]
                )
            pass
    else:
        add_annotation_form = forms.AddAnnotationForm(
            [record.location for record in records]
        )

    if not records.exists():
        pass  # TODO: raise

    null_checksum_locations = [
        location for location, record in locations.items()
        if record is not None and record.checksum is None
    ]

    return render(
        request, "inventory/collection/record.html", {
            "collections": models.Collection.objects.all(),
            "collection": collection, "filename": filename,
            "fields": display_fields,
            "locations": locations, "records": records,
            "differences": differences,
            "checksum_mismatch": checksum_mismatch,
            "null_checksum_locations": null_checksum_locations,
            "add_annotation_form": add_annotation_form
        }
    )


@login_required(login_url="login")
@check_collection
def annotation_add_view(request, mission, file_type, filename):
    """ Django view function to create an annotation for a record.
    """
    if request.method == "POST":
        collection = models.Collection.objects.get(
            mission=mission, file_type=file_type
        )
        records = models.Record.objects.filter(
            filename=filename, location__collection=collection
        )

        form = forms.AddAnnotationForm(
            [record.location for record in records], request.POST
        )
        if form.is_valid():
            data = form.cleaned_data
            annotation_records = [
                models.Record.objects.get(
                    filename=filename, location=data["location"]
                )
            ] if data["location"] else records
            for record in annotation_records:
                models.Annotation.objects.create(
                    record=record, text=data["text"]
                )

            messages.info(request, "Added annotation.")
        else:
            return record_view(request, mission, file_type, filename)

    return redirect("inventory:collection:record",
        mission=mission, file_type=file_type, filename=filename
    )


@login_required(login_url="login")
def annotation_delete_view(request, mission, file_type, filename):
    """ Django view function to delete a specific annotation.
    """
    if request.method == "POST":
        models.Annotation.objects.get(pk=request.POST["annotation"]).delete()
        messages.info(request, "Removed annotation.")

    return redirect("inventory:collection:record",
        mission=mission, file_type=file_type, filename=filename
    )


@login_required(login_url="login")
@check_collection
def alignment_view(request, mission, file_type):
    """ Django view function to perform the alignment check.
    """
    collection = models.Collection.objects.get(
        mission=mission, file_type=file_type
    )

    config = collection.configuration

    records = None
    locations = None
    locations_with_no_checksum = None
    frmt = "html"
    if request.method == "POST":
        form = forms.AlignmentForm(
            collection.locations.all(), config.available_alignment_fields or [],
            request.POST
        )
        pagination_form = forms.PaginationForm(request.POST)
        if form.is_valid() and pagination_form.is_valid():
            frmt = form.cleaned_data.pop("format")
            observer = monitor(
                "alignment_check", mission=mission, file_type=file_type,
                **form.cleaned_data
            )
            with observer:
                locations, qs = queries.alignment(collection, form.cleaned_data)
            page = pagination_form.cleaned_data.pop("page")
            per_page = pagination_form.cleaned_data.pop("records_per_page")

            if frmt == "html":
                records = Paginator(qs, per_page).page(page)
            else:
                records = qs

            locations_with_no_checksum = [
                location for location in locations or []
                if collection.get_metadata_field_mapping(location).get("checksum") is None
            ]
    else:
        form = forms.AlignmentForm(
            collection.locations.all(), config.available_alignment_fields or []
        )
        pagination_form = forms.PaginationForm(
            initial={'page': '1', 'records_per_page': '15'}
        )

    if frmt == "html":
        return render(
            request, "inventory/collection/alignment.html", {
                "collections": models.Collection.objects.all(),
                "collection": collection, "alignment_form": form,
                "pagination_form": pagination_form, "records": records,
                "locations": locations,
                "locations_with_no_checksum": locations_with_no_checksum
            }
        )
    elif frmt in ("csv", "tsv"):
        f = tempfile.SpooledTemporaryFile()
        writer = csv.writer(f, delimiter="," if frmt == "csv" else "\t")
        writer.writerow(
            ["filename"] + [l.url for l in locations] + ["annotations"]
        )
        for row in qs:
            writer.writerow(
                [row["filename"]] + list(row["incidences"]) +
                list(row["annotations"])
            )

        size = f.tell()
        f.seek(0)

        response = StreamingHttpResponse(f, content_type="text/csv")
        response["Content-Length"] = str(size)
        response["Content-Disposition"] = (
            'inline; filename="alignment-%s.csv"' % (
                now().replace(microsecond=0, tzinfo=None).isoformat("T")
            )
        )
        return response


@permission_required("inventory.can_export", raise_exception=True)
@check_collection
def export_view(request, mission, file_type):
    """ Django view function to export configuration and data.
    """
    collection = models.Collection.objects.get(
        mission=mission, file_type=file_type
    )

    if request.method == "POST":
        form = forms.ImportExportBaseForm(request.POST)
        if form.is_valid():
            selection = form.cleaned_data["selection"]
            configuration = False
            data = False
            if selection == "full":
                configuration = True
                data = True
            elif selection == "config":
                configuration = True
            elif selection == "data":
                data = True

            try:
                filename = export_collection(
                    mission, file_type, None, configuration, data
                )
                messages.info(request,
                    "Exported collection %s to file %s" % (
                        collection, basename(filename)
                    )
                )
            except Exception:
                messages.error("Failed to export collection %s" % collection)
        else:
            messages.error(request,
                "Failed to start export for collection %s" % collection
            )
        return redirect("inventory:collection:export",
            mission=mission, file_type=file_type
        )

    form = forms.ImportExportBaseForm()
    return render(
        request, "inventory/collection/export.html", {
            "collections": models.Collection.objects.all(),
            "collection": collection, "form": form,
            "exports": list_exports(mission, file_type)
        }
    )


@login_required(login_url="login")
@check_collection
def import_view(request, mission, file_type):
    """ Django view function to import configuration and data.
    """
    collection = models.Collection.objects.get(
        mission=mission, file_type=file_type
    )

    form = forms.ImportForm(
        tuple((export, export) for export in list_exports(mission, file_type))
    )
    return render(
        request, "inventory/collection/import.html", {
            "collections": models.Collection.objects.all(),
            "collection": collection, "form": form
        }
    )


@login_required(login_url="login")
@check_collection
def download_export_view(request, mission, file_type, filename):
    """ Django view function to download a previously exported archive.
    """
    collection = models.Collection.objects.get(
        mission=mission, file_type=file_type
    )
    if filename not in list_exports(mission, file_type):
        raise Http404("No such export '%s'" % filename)

    return StreamingHttpResponse(
        open(join(collection.data_dir, "exports", filename), "rb"),
        content_type="application/zip"
    )


def _generate_mapping_formsets(collection, config=None, POST=None):
    if POST:
        formsets = [
            (None, forms.MetadataMappingFormset(POST, prefix="default"))
        ]
        formsets.extend([
            (location, forms.MetadataMappingFormset(
                POST, prefix="location_%d" % location.pk)
            )
            for location in collection.locations.all().order_by("pk")
        ])
    else:
        formsets = [
            (None, forms.MetadataMappingFormset(prefix="default", initial=[
                {"search_key": key, "index_file_key": v}
                for key, v in config.default_metadata_mapping.items()
            ]))
        ]
        formsets.extend([
            (location, forms.MetadataMappingFormset(
                prefix="location_%d" % location.pk, initial=[
                    {"search_key": key, "index_file_key": v}
                    for key, v in config.get_section_dict(
                        "metadata_mapping.%s" % location.url,
                        ordered=True
                    ).items()
                ])
            )
            for location in collection.locations.all().order_by("pk")
        ])

    return formsets


@login_required(login_url="login")
@permission_required("inventory.can_configure_collections", raise_exception=True)
@check_collection
def configuration_view(request, mission, file_type):
    """ View function to provide a change form for the collections configuration.
    For the metadata mapping a seperate formset is used.
    """
    collection = models.Collection.objects.get(
        mission=mission, file_type=file_type
    )

    config = collection.configuration

    if request.method == "POST":
        configuration_form = forms.CollectionConfigurationForm(request.POST)
        mapping_formsets = _generate_mapping_formsets(
            collection, POST=request.POST
        )

        mapping_formsets_valid = all([
            f[1].is_valid() for f in mapping_formsets
        ])

        if configuration_form.is_valid() and mapping_formsets_valid:
            for key, value in configuration_form.cleaned_data.items():
                setattr(config, key, value)

            for location, mapping_formset in mapping_formsets:
                mapping = SortedDict()
                for form in mapping_formset:
                    if form.is_valid():
                        data = form.cleaned_data
                        if data.get("DELETE") or not data.get("index_file_key"):
                            continue
                        mapping[data["search_key"]] = data["index_file_key"]

                if location:
                    config.set_section_dict(
                        "metadata_mapping.%s" % location.url, mapping
                    )
                else:
                    config.default_metadata_mapping = mapping

            errors = check_collection_configuration(config)

            if errors:
                for error in errors:
                    messages.error(request, error)
            else:
                backup_config(config._config_path)
                config.write()
                messages.info(request,
                    "Saved configuration for collection %s." % collection
                )

            # re-read the forms here with the updated configuration
            config.read(reset=True)

            configuration_form = forms.CollectionConfigurationForm(
                initial={
                    "export_interval": timedelta_to_duration(
                        config.export_interval
                    ),
                    "harvest_interval": timedelta_to_duration(
                        config.harvest_interval
                    ),
                    "available_result_list_fields":
                        config.available_result_list_fields,
                    "available_alignment_fields":
                        config.available_alignment_fields
                }
            )
            mapping_formsets = _generate_mapping_formsets(
                collection, config=config
            )

    else:
        configuration_form = forms.CollectionConfigurationForm(
            initial={
                "export_interval": timedelta_to_duration(
                    config.export_interval
                ),
                "harvest_interval": timedelta_to_duration(
                    config.harvest_interval
                ),
                "available_result_list_fields":
                    config.available_result_list_fields,
                "available_alignment_fields":
                    config.available_alignment_fields
            }
        )
        mapping_formsets = _generate_mapping_formsets(
            collection, config=config
        )

    return render(
        request, "inventory/collection/configuration.html", {
            "collections": models.Collection.objects.all(),
            "collection": collection, "configuration_form": configuration_form,
            "mapping_formsets": mapping_formsets
        }
    )
