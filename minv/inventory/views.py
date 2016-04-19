from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from minv.inventory import models
from minv.inventory import forms


@login_required(login_url="login")
def backup_view(request):
    """ Django view to show and create backups.
    """
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
    """ Django view to restore previously created backups
    """
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
