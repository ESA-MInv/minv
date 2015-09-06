from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

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
def backup_view(request):
    if request.method == "POST":
        form = forms.BackupForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            messages.info(
                request, "Started %s backup of %s." % (
                    data["backup_type"], ", ".join(data["subject"])
                )
            )
    else:
        form = forms.BackupForm()
    return render(
        request, "inventory/backup.html", {
            "collections": models.Collection.objects.all(),
            "form": form
        }
    )


@login_required(login_url="login")
def restore_view(request):
    if request.method == "POST":
        form = forms.RestoreForm(request.POST)
        if form.is_valid():
            messages.info(
                request,
                "Restored instance from '%s'." % form.cleaned_data["backup"]
            )
    else:
        form = forms.RestoreForm()
    return render(
        request, "inventory/restore.html", {
            "collections": models.Collection.objects.all(),
            "form": form
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
