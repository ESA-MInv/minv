from django.shortcuts import render
from django.shortcuts import redirect
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
