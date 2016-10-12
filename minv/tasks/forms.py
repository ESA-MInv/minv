# ------------------------------------------------------------------------------
#
# Project: Master Inventory <http://github.com/ESA-MInv/minv>
# Authors: Fabian Schindler <fabian.schindler@eox.at>
#
# ------------------------------------------------------------------------------
# Copyright (C) 2016 European Space Agency
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies of this Software or works derived from this Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
# ------------------------------------------------------------------------------


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
