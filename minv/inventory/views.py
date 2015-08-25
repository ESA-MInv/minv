from django.shortcuts import render

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


def collection_search(request, mission, file_type):
    if request.method == "POST":
        form = forms.RecordSearchForm(request.POST)
        if form.is_valid():
            print form.cleaned_data
            pass
    else:
        form = forms.RecordSearchForm()
    collection = models.Collection.objects.get(
        mission=mission, file_type=file_type
    )
    return render(
        request, "inventory/collection_search.html", {
            "collections": models.Collection.objects.all(),
            "collection": collection, "search_form": form
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


def task_monitor(request):
    qs = monitor_models.Task.objects.all().order_by("start_time")

    print request.POST
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
