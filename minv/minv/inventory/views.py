from os.path import join
from ConfigParser import RawConfigParser
import json

from django.shortcuts import render
from django.core.paginator import Paginator
from django.shortcuts import redirect
from django.contrib import messages
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from minv.inventory import models
from minv.inventory import forms
from minv.monitor import models as monitor_models

# Create your views here.


def login_view(request):
    logout(request)
    username = password = ''
    if request.POST:
        username = request.POST['username']
        password = request.POST['password']
        next_ = request.POST.get('next')

        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                if next_:
                    return redirect(next_)
                return redirect('inventory:root')
    return render(
        request, 'inventory/login.html', {"next": request.GET.get("next")}
    )


def logout_view(request):
    logout(request)
    next_ = request.GET.get("next")
    if next_:
        return redirect(next_)
    return redirect('inventory:root')


@login_required(login_url="login")
def root_view(request):
    return render(
        request, "inventory/root.html", {
            "collections": models.Collection.objects.all()
        }
    )


@login_required(login_url="login")
def collection_list_view(request):
    return render(
        request, "inventory/collection_list.html", {
            "collections": models.Collection.objects.all()
        }
    )


@login_required(login_url="login")
def collection_detail_view(request, mission, file_type):
    collection = models.Collection.objects.get(
        mission=mission, file_type=file_type
    )
    return render(
        request, "inventory/collection_detail.html", {
            "collections": models.Collection.objects.all(),
            "collection": collection
        }
    )


@login_required(login_url="login")
def collection_harvest_view(request, mission, file_type):
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


@login_required(login_url="login")
def collection_search_view(request, mission, file_type):
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
                    if not value:
                        continue
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


@login_required(login_url="login")
def collection_alignment_view(request, mission, file_type):
    collection = models.Collection.objects.get(
        mission=mission, file_type=file_type
    )
    if request.method == "POST":
        form = forms.AlignmentForm(request.POST)
        if form.is_valid():
            # print form.cleaned_data
            pass
    else:
        form = forms.RecordSearchForm(collection.locations.all())
    return render(
        request, "inventory/collection_alignment.html", {
            "collections": models.Collection.objects.all(),
            "collection": collection, "alignment_form": form
        }
    )


@login_required(login_url="login")
def collection_export_view(request, mission, file_type):
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
        request, "inventory/collection_export.html", {
            "collections": models.Collection.objects.all(),
            "collection": collection, "form": form
        }
    )


@login_required(login_url="login")
def collection_import_view(request, mission, file_type):
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


@login_required(login_url="login")
def collection_configuration_view(request, mission, file_type):
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
        request, "inventory/collection_configuration.html", {
            "collections": models.Collection.objects.all(),
            "collection": collection, "configuration_form": configuration_form,
            "mapping_formset": mapping_formset
        }
    )


@login_required(login_url="login")
def task_monitor_view(request):
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
