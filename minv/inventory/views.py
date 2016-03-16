from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from minv.inventory import models
from minv.inventory import forms


def login_view(request):
    """ Django view to log in as a user. Logs out when the user was logged in
    before.
    """
    logout(request)
    username = password = ''
    login_error = None
    if request.POST:
        username = request.POST['username']
        password = request.POST['password']
        next_ = request.POST.get('next')

        user = authenticate(username=username, password=password)
        if user is not None and user.is_active:
            login(request, user)
            if next_:
                return redirect(next_)
            return redirect('inventory:root')
        else:
            login_error = True
    return render(
        request, 'inventory/login.html', {
            "next": request.GET.get("next"),
            "login_error": login_error
        }
    )


def logout_view(request):
    """ Django view to log out the current user.
    """
    logout(request)
    next_ = request.GET.get("next")
    if next_:
        return redirect(next_)
    return redirect('inventory:root')


@login_required(login_url="login")
def root_view(request):
    """ The root view of the Master Inventory.
    """
    return render(
        request, "inventory/root.html", {
            "collections": models.Collection.objects.all()
        }
    )


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
