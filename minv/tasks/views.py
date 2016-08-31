from django.shortcuts import render, redirect
from django.utils.timezone import now
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator

from minv.tasks import models
from minv.tasks import forms
from minv.tasks.api import restart_job
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
        pagination_form = inventory_forms.PaginationForm(
            request.POST, initial={'page': page, 'records_per_page': per_page}
        )
        if filter_form.is_valid():
            if filter_form.cleaned_data["status"]:
                qs = qs.filter(status=filter_form.cleaned_data["status"])
            if filter_form.cleaned_data["task"]:
                qs = qs.filter(task=filter_form.cleaned_data["task"])

        if pagination_form.is_valid():
            page = pagination_form.cleaned_data.pop("page")
            per_page = pagination_form.cleaned_data.pop(
                "records_per_page"
            )
    else:
        filter_form = forms.JobFilterForm()
        pagination_form = inventory_forms.PaginationForm(initial={
            "records_per_page": per_page, "page": page
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
                messages.info(request, "Scheduled restart of job '%s'." % job)
                restart_job(job)
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
            "job": job,
            "form": form,
            "is_restartable": job.task in (
                "harvest", "export", "import", "backup", "restore"
            )
        }
    )
