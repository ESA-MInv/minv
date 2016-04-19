from django.shortcuts import render, redirect
from django.utils.timezone import now
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from minv.tasks import models
from minv.tasks import forms
from minv.inventory import models as inventory_models


@login_required(login_url="login")
def job_list_view(request):
    """ Django view to show an overview list of all running, finished, errored
    etc jobs.
    """
    qs = models.Job.objects.all().order_by("start_time")
    if request.method == "POST":
        form = forms.JobFilterForm(request.POST)
        if form.is_valid() and form.cleaned_data["status"]:
            qs = qs.filter(status=form.cleaned_data["status"])

    else:
        form = forms.JobFilterForm()
    return render(
        request, "tasks/job_list.html", {
            "collections": inventory_models.Collection.objects.all(),
            "jobs": qs, "filter_form": form
        }
    )


@login_required(login_url="login")
def job_view(request, job_id):
    """ Django view to show the details of a single job and allow interactions.
    """
    job = models.Job.objects.get(id=job_id)
    if request.method == "POST":
        form = forms.JobActionForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data["action"]
            if action == "restart":
                job.start_time = now()
                job.end_time = None
                job.status = "running"
                job.full_clean()
                job.save()
                messages.info(request, "Job '%s' restarted." % job)
            elif action == "abort":
                if job.status != "running":
                    messages.error(request, "Job '%s' was not running." % job)
                else:
                    job.status = "aborted"
                    job.end_time = now()
                    job.full_clean()
                    job.save()
                    messages.info(request, "Job '%s' aborted." % job)
            elif action == "remove":
                messages.info(request, "Job '%s' removed." % job)
                job.delete()
                return redirect("inventory:tasks:job-list")

    else:
        form = forms.JobActionForm()
    return render(
        request, "tasks/job.html", {
            "collections": inventory_models.Collection.objects.all(),
            "job": job, "form": form
        }
    )
