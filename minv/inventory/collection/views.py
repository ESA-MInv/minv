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

from minv.inventory.views import login_required
from minv.inventory import models
from minv.inventory import forms
from minv.inventory import queries
from minv.inventory.collection.export import (
    export_collection, import_collection, list_exports
)
from minv.utils import get_or_none


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

    for url in request.GET.getlist("url"):
        messages.info(request, "Harvesting URL %s for collection %s" % (
            url, collection
        ))
        messages.success(request, "Harvesting URL %s for collection %s" % (
            url, collection
        ))
        messages.warning(request, "Harvesting URL %s for collection %s" % (
            url, collection
        ))
        messages.error(request, "Harvesting URL %s for collection %s" % (
            url, collection
        ))

    return redirect("inventory:collection:detail",
        mission=mission, file_type=file_type
    )


@login_required(login_url="login")
@check_collection
def search_view(request, mission, file_type):
    """ Django view function to perform the collection search.
    """
    collection = models.Collection.objects.get(
        mission=mission, file_type=file_type
    )

    records = None
    if request.method == "POST":
        form = forms.RecordSearchForm(collection.locations.all(), request.POST)
        pagination_form = forms.PaginationForm(request.POST)
        if form.is_valid() and pagination_form.is_valid():
            qs = queries.search(collection, form.cleaned_data)
            page = pagination_form.cleaned_data.pop("page")
            per_page = pagination_form.cleaned_data.pop("records_per_page")
            records = Paginator(qs, per_page).page(page)
    else:
        form = forms.RecordSearchForm(collection.locations.all())
        pagination_form = forms.PaginationForm(
            initial={'page': '1', 'records_per_page': '15'}
        )

    return render(
        request, "inventory/collection/search.html", {
            "collections": models.Collection.objects.all(),
            "collection": collection, "search_form": form,
            "pagination_form": pagination_form, "records": records
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

    return render(
        request, "inventory/collection/record.html", {
            "collections": models.Collection.objects.all(),
            "collection": collection, "filename": filename,
            "fields": display_fields,
            "locations": locations, "records": records,
            "differences": differences,
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
    frmt = "html"
    if request.method == "POST":
        form = forms.AlignmentForm(
            collection.locations.all(), config.available_alignment_fields or [],
            request.POST
        )
        pagination_form = forms.PaginationForm(request.POST)
        if form.is_valid() and pagination_form.is_valid():
            frmt = form.cleaned_data.pop("format")
            locations, qs = queries.alignment(collection, form.cleaned_data)
            page = pagination_form.cleaned_data.pop("page")
            per_page = pagination_form.cleaned_data.pop("records_per_page")
            records = Paginator(qs, per_page).page(page)
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
                "locations": locations
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


@login_required(login_url="login")
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


@login_required(login_url="login")
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
        mapping_formset = forms.MetadataMappingFormset(request.POST)

        if configuration_form.is_valid() and mapping_formset.is_valid():
            for key, value in configuration_form.cleaned_data.items():
                print key, value
                setattr(config, key, value)

            mapping = {}
            for form in mapping_formset:
                if form.is_valid():
                    data = form.cleaned_data
                    if data["DELETE"] or not data["index_file_key"]:
                        continue
                    mapping[data["search_key"]] = data["index_file_key"]

            config.metadata_mapping = mapping
            config.write()
            messages.info(request,
                "Saved configuration for collection %s." % collection
            )

            # re-read the forms here with the updated configuration
            config.read(reset=True)

            configuration_form = forms.CollectionConfigurationForm(
                initial={
                    "export_interval": config.export_interval,
                    "harvest_interval": config.harvest_interval,
                    "available_alignment_fields":
                        config.available_alignment_fields
                }
            )
            mapping_formset = forms.MetadataMappingFormset(initial=[
                {"search_key": key, "index_file_key": v}
                for key, v in config.metadata_mapping.items()
            ])

    else:
        configuration_form = forms.CollectionConfigurationForm(
            initial={
                "export_interval": config.export_interval,
                "harvest_interval": config.harvest_interval,
                "available_alignment_fields":
                    config.available_alignment_fields
            }
        )
        mapping_formset = forms.MetadataMappingFormset(initial=[
            {"search_key": key, "index_file_key": v}
            for key, v in config.metadata_mapping.items()
        ])

    return render(
        request, "inventory/collection/configuration.html", {
            "collections": models.Collection.objects.all(),
            "collection": collection, "configuration_form": configuration_form,
            "mapping_formset": mapping_formset
        }
    )
