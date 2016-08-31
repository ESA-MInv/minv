from django import forms
from minv.tasks import models


class JobFilterForm(forms.Form):
    status = forms.ChoiceField(
        required=False,
        choices=(("", "All"), ("pending", "Pending"), ("running", "Running"),
                 ("finished", "Finished"), ("failed", "Failed"),
                 ("aborted", "Aborted")),
        widget=forms.Select(attrs={"class": "form-control"})
    )

    def __init__(self, *args, **kwargs):
        super(JobFilterForm, self).__init__(*args, **kwargs)
        self.fields["task"] = forms.ChoiceField(
            required=False,
            choices=[("", "All")] + [
                (name, name)
                for name in models.Job.objects.distinct('task').values_list(
                    'task', flat=True
                )
            ],
            widget=forms.Select(attrs={"class": "form-control"})
        )


class JobActionForm(forms.Form):
    action = forms.ChoiceField(
        choices=(
            ("restart", "Restart"), ("abort", "Abort"), ("remove", "Remove")
        ),
        widget=forms.Select(attrs={"class": "form-control"})
    )
