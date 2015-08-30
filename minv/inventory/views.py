from django.shortcuts import render
from django.core.paginator import Paginator
from django.shortcuts import redirect
from django.contrib import messages

from inventory import models
from inventory import forms
from monitor import models as monitor_models

# Create your views here.


def collection_list(request):
    return render(
        request, "inventory/collection_list.html", {
            "collections": models.Collection.objects.all()
        }
    )


def collection_detail(request, mission, file_type):
    collection = models.Collection.objects.get(
        mission=mission, file_type=file_type
    )
    return render(
        request, "inventory/collection_detail.html", {
            "collections": models.Collection.objects.all(),
            "collection": collection
        }
    )


def collection_harvest(request, mission, file_type):
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

    return redirect("inventory:collection-detail",
        mission=mission, file_type=file_type
    )


def collection_search(request, mission, file_type):
    collection = models.Collection.objects.get(
        mission=mission, file_type=file_type
    )

    records = None
    if request.method == "POST":
        form = forms.RecordSearchForm(collection.locations.all(), request.POST)
        if form.is_valid():
            qs = models.Record.objects.filter(location__collection=collection)
            page = form.cleaned_data.pop("page")
            records_per_page = form.cleaned_data.pop("records_per_page")
            for key, value in form.cleaned_data.items():
                if value is None or value == "":
                    continue
                if key == "locations":
                    filter_ = {"location__in": value}
                elif isinstance(value, list):
                    low, high = value
                    if key == "acquisition_date":
                        key_low = "begin_date"
                        key_high = "end_date"
                    else:
                        key_low = key
                        key_high = key

                    filter_ = {
                        "%s__lte" % key_low: high, "%s__gte" % key_high: low
                    }

                else:
                    filter_ = {key: value}

                qs = qs.filter(**filter_)

        records = Paginator(qs, records_per_page).page(page or 1)

    else:
        form = forms.RecordSearchForm(
            collection.locations.all(),
            initial={'page': '1', 'records_per_page': '15'}
        )

    return render(
        request, "inventory/collection_search.html", {
            "collections": models.Collection.objects.all(),
            "collection": collection, "search_form": form,
            "records": records
        }
    )


def collection_alignment(request, mission, file_type):
    if request.method == "POST":
        form = forms.AlignmentForm(request.POST)
        if form.is_valid():
            # print form.cleaned_data
            pass
    else:
        form = forms.RecordSearchForm()
    collection = models.Collection.objects.get(
        mission=mission, file_type=file_type
    )
    return render(
        request, "inventory/collection_alignment.html", {
            "collections": models.Collection.objects.all(),
            "collection": collection, "alignment_form": form
        }
    )


def collection_export(request, mission, file_type):
    collection = models.Collection.objects.get(
        mission=mission, file_type=file_type
    )

    if request.method == "POST":
        form = forms.ImportExportBaseForm(request.POST)
        if form.is_valid():
            messages.info(request, "Started export for collection %s" % collection)
        else:
            messages.error(request, "Failed to start export for collection %s" % collection)
        return redirect("inventory:collection-export",
            mission=mission, file_type=file_type
        )

    form = forms.ImportExportBaseForm()
    return render(
        request, "inventory/collection_export.html", {
            "collections": models.Collection.objects.all(),
            "collection": collection, "form": form
        }
    )


def collection_import(request, mission, file_type):
    collection = models.Collection.objects.get(
        mission=mission, file_type=file_type
    )
    form = forms.ImportForm((("export_20150829.dat", "export_20150829.dat"),))
    return render(
        request, "inventory/collection_import.html", {
            "collections": models.Collection.objects.all(),
            "collection": collection, "form": form
        }
    )


def task_monitor(request):
    qs = monitor_models.Task.objects.all().order_by("start_time")
    if request.method == "POST":
        form = forms.TaskFilterForm(request.POST)
        if form.is_valid() and form.cleaned_data["status"]:
            qs = qs.filter(status=form.cleaned_data["status"])

    else:
        form = forms.TaskFilterForm()
    return render(
        request, "inventory/task_monitor.html", {
            "collections": models.Collection.objects.all(),
            "tasks": qs, "filter_form": form
        }
    )
