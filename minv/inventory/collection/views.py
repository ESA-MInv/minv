from os.path import join
from ConfigParser import RawConfigParser
import json
from functools import wraps

from django.shortcuts import render
from django.core.paginator import Paginator
from django.shortcuts import redirect
from django.contrib import messages
from django.conf import settings

from minv.inventory.views import login_required
from minv.inventory import models
from minv.inventory import forms
from minv.inventory import queries


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
    return render(
        request, "inventory/collection/list.html", {
            "collections": models.Collection.objects.all()
        }
    )


@login_required(login_url="login")
@check_collection
def detail_view(request, mission, file_type):
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
    pass


@login_required(login_url="login")
@check_collection
def alignment_view(request, mission, file_type):
    collection = models.Collection.objects.get(
        mission=mission, file_type=file_type
    )
    locations = results = None
    if request.method == "POST":
        form = forms.AlignmentForm(collection.locations.all(), request.POST)
        if form.is_valid():
            locations, results = queries.alignment_new(
                collection, form.cleaned_data
            )
    else:
        form = forms.AlignmentForm(collection.locations.all())
    return render(
        request, "inventory/collection/alignment.html", {
            "collections": models.Collection.objects.all(),
            "collection": collection, "alignment_form": form,
            "locations": locations, "results": results
        }
    )


@login_required(login_url="login")
@check_collection
def export_view(request, mission, file_type):
    collection = models.Collection.objects.get(
        mission=mission, file_type=file_type
    )

    if request.method == "POST":
        form = forms.ImportExportBaseForm(request.POST)
        if form.is_valid():
            messages.info(request,
                "Started export for collection %s" % collection
            )
        else:
            messages.error(request,
                "Failed to start export for collection %s" % collection
            )
        return redirect("inventory:collection-export",
            mission=mission, file_type=file_type
        )

    form = forms.ImportExportBaseForm()
    return render(
        request, "inventory/collection/export.html", {
            "collections": models.Collection.objects.all(),
            "collection": collection, "form": form
        }
    )


@login_required(login_url="login")
@check_collection
def import_view(request, mission, file_type):
    collection = models.Collection.objects.get(
        mission=mission, file_type=file_type
    )
    form = forms.ImportForm((("export_20150829.dat", "export_20150829.dat"),))
    return render(
        request, "inventory/collection/import.html", {
            "collections": models.Collection.objects.all(),
            "collection": collection, "form": form
        }
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

    with open(join(settings.BASE_DIR, "minv_prototype/minv.conf")) as f:
        parser = RawConfigParser()
        parser.readfp(f)

    if request.method == "POST":
        configuration_form = forms.CollectionConfigurationForm(request.POST)
        mapping_formset = forms.MetadataMappingFormset(request.POST)
        if configuration_form.is_valid() and mapping_formset.is_valid():
            for key, value in configuration_form.cleaned_data.items():
                parser.set("inventory", key, value)
            with open(join(settings.BASE_DIR, "minv_prototype/minv.conf"), "w") as f:
                parser.write(f)

            mapping = {}
            for form in mapping_formset:
                if form.is_valid():  # and not form.has_changed():
                    data = form.cleaned_data
                    mapping[data["search_key"]] = data["index_file_key"]

            with open(join(settings.BASE_DIR, "minv_prototype/mapping.json"), "w") as f:
                json.dump(mapping, f, indent=2)
    else:
        configuration_form = forms.CollectionConfigurationForm(
            initial=dict(parser.items("inventory"))
        )
        with open(join(settings.BASE_DIR, "minv_prototype/mapping.json")) as f:
            data = json.load(f)
            initial = [
                {"search_key": key, "index_file_key": value}
                for key, value in data.items()
            ]
        mapping_formset = forms.MetadataMappingFormset(initial=initial)
    return render(
        request, "inventory/collection/configuration.html", {
            "collections": models.Collection.objects.all(),
            "collection": collection, "configuration_form": configuration_form,
            "mapping_formset": mapping_formset
        }
    )
