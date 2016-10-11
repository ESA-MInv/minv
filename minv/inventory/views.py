from os.path import join, basename

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from minv.inventory import models
from minv.inventory import forms
from minv.inventory.backup import (
    backup, restore, get_available_backups, BASE_PATH
)


def get_available_backups_list(add_no_selected=False):
    files = [
        (bck[0], "%s (%s)" % bck)
        for bck in get_available_backups()
    ]

    return files if not add_no_selected else [("", "----")] + files


@login_required(login_url="login")
def backup_view(request):
    """ Django view to show and create backups.
    """
    if request.method == "POST":
        form = forms.BackupForm(get_available_backups_list(True), request.POST)
        if form.is_valid():
            data = form.cleaned_data

            backup_type = data.get("backup_type")
            subject = data.get("subject", [])
            configuration = "configuration" in subject
            logs = "logfiles" in subject

            try:
                diff = data.get("differential_file")
                interval = data.get("interval")
                if backup_type == "incremental" and not interval:
                    raise Exception(
                        "Backup type is incremental, but no interval specified"
                    )
                elif backup_type == "incremental":
                    diff = None

                if backup_type == "differential" and not diff:
                    raise Exception(
                        "Backup type is differential, but no base backup file "
                        "selected."
                    )
                elif backup_type == "differential":
                    diff = join(BASE_PATH, diff)
                    interval = None

                if backup_type == "full":
                    diff = None
                    interval = None

                backup_path = backup(logs, configuration, False, diff, interval)
            except Exception as exc:
                messages.error(
                    request, "Failed to perform backup, error was: %s" % exc
                )
            else:
                messages.info(
                    request, "Created %s backup of %s: %s." % (
                        data["backup_type"], ", ".join(data["subject"]),
                        basename(backup_path)
                    )
                )
                form = forms.BackupForm(
                    get_available_backups_list(True), request.POST
                )
    else:
        form = forms.BackupForm(get_available_backups_list(True))
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
        form = forms.RestoreForm(get_available_backups_list(), request.POST)
        if form.is_valid():
            filename = form.cleaned_data["backup"]
            try:

                restore(join(BASE_PATH, filename))
            except Exception as exc:
                messages.error(
                    request,
                    "Failed to restore backup from '%s', error was: %s"
                    % (filename, exc)
                )
            else:
                messages.info(
                    request,
                    "Restored backup from '%s'." % filename
                )
    else:
        form = forms.RestoreForm(get_available_backups_list())
    return render(
        request, "inventory/restore.html", {
            "collections": models.Collection.objects.all(),
            "form": form
        }
    )
