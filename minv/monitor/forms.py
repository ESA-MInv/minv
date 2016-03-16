from django import forms


class JobFilterForm(forms.Form):
    status = forms.ChoiceField(
        required=False,
        choices=(("", "All"), ("pending", "Pending"), ("running", "Running"),
                 ("finished", "Finished"), ("failed", "Failed"),
                 ("aborted", "Aborted")),
        widget=forms.Select(
            attrs={"class": "form-control"}
        )
    )

    def __init__(self):
        super(JobFilterForm, self).__init__()
        self.fields["task"] = forms.ChoiceField(
            required=False,
            choices=(("", "All"), ),
            widget=forms.Select(
                attrs={"class": "form-control"}
            )
        )


class JobActionForm(forms.Form):
    action = forms.ChoiceField(
        choices=(
            ("restart", "Restart"), ("abort", "Abort"), ("remove", "Remove")
        ),
        widget=forms.Select(
            attrs={"class": "form-control"}
        )
    )
