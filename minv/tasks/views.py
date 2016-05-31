from django.shortcuts import render, redirect
from django.utils.timezone import now
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator

from minv.tasks import models
from minv.tasks import forms
from minv.inventory import forms as inventory_forms
from minv.inventory import models as inventory_models


@login_required(login_url="login")
def job_list_view(request):
    """ Django view to show an overview list of all running, finished, errored
    etc jobs.
    """

    qs = models.Job.objects.all().order_by("-start_time")
    scheduled_jobs = models.ScheduledJob.objects.all().order_by("-when")

    page = 1
    per_page = 15

    if request.method == "POST":
        filter_form = forms.JobFilterForm(request.POST)
        pagination_form = inventory_forms.PaginationForm(request.POST)
        if filter_form.is_valid() and filter_form.cleaned_data["status"]:
            qs = qs.filter(status=filter_form.cleaned_data["status"])

        if pagination_form.is_valid():
            page = pagination_form.cleaned_data.pop("page")
            per_page = pagination_form.cleaned_data.pop(
                "records_per_page"
            )
    else:
        filter_form = forms.JobFilterForm()
        pagination_form = inventory_forms.PaginationForm({
            "per_page": per_page, "page": page
        })

    jobs = Paginator(qs, per_page).page(page)
    return render(
        request, "tasks/job_list.html", {
            "collections": inventory_models.Collection.objects.all(),
            "jobs": jobs, "scheduled_jobs": scheduled_jobs,
            "filter_form": filter_form,
            "pagination_form": pagination_form
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

                # TODO: actually restart job

                return redirect("tasks:job", job_id=job_id)
            elif action == "abort":
                if job.status != "running":
                    messages.error(request, "Job '%s' was not running." % job)
                else:
                    job.status = "aborted"
                    job.end_time = now()
                    job.full_clean()
                    job.save()
                    messages.info(request, "Job '%s' aborted." % job)

                    # TODO: actually abort

                return redirect("tasks:job", job_id=job_id)
            elif action == "remove":
                messages.info(request, "Job '%s' removed." % job)
                job.delete()
                return redirect("tasks:job-list")

    else:
        form = forms.JobActionForm()
    return render(
        request, "tasks/job.html", {
            "collections": inventory_models.Collection.objects.all(),
            "job": job, "form": form
        }
    )
