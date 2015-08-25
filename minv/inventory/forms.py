from django import forms
from django.db import models
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _
from django.core.validators import RegexValidator

from inventory import models as inventory_models


class RangeWidget(forms.MultiWidget):
    def __init__(self, widget, *args, **kwargs):
        widgets = (widget, widget)

        super(RangeWidget, self).__init__(widgets=widgets, *args, **kwargs)

    def decompress(self, value):
        print value
        return value or []

    """
    def format_output(self, rendered_widgets):
        widget_context = {
            'min': rendered_widgets[0], 'max': rendered_widgets[1],
        }
        return render_to_string('inventory/range_widget.html', widget_context)

    """


class RangeField(forms.MultiValueField):
    default_error_messages = {
        'invalid_start': _(u'Enter a valid start value.'),
        'invalid_end': _(u'Enter a valid end value.'),
    }

    def __init__(self, field_class, widget=forms.TextInput, *args, **kwargs):
        if not 'initial' in kwargs:
            kwargs['initial'] = ['', '']

        fields = (field_class(), field_class())

        super(RangeField, self).__init__(
            fields=fields,
            widget=RangeWidget(widget),
            *args, **kwargs
        )

    def compress(self, data_list):
        if data_list:
            return [
                self.fields[0].clean(data_list[0]),
                self.fields[1].clean(data_list[1])
            ]

        return None


class RecordSearchForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(RecordSearchForm, self).__init__(*args, **kwargs)
        for field in inventory_models.Record._meta.fields:
            # TODO: make ranges
            attrs = {"class": "form-control"}
            if isinstance(field, models.IntegerField):
                self.fields[field.name] = RangeField(
                    forms.IntegerField, widget=forms.NumberInput(attrs=attrs),
                    required=False
                )
            elif isinstance(field, models.FloatField):
                self.fields[field.name] = RangeField(
                    forms.FloatField, widget=forms.NumberInput(attrs=attrs),
                    required=False
                )
            elif isinstance(field, models.CharField):
                if field.choices:
                    self.fields[field.name] = forms.ChoiceField(
                        required=False, choices=((None, "---"),) + field.choices,
                        widget=forms.Select(attrs={"class": "form-control"})
                    )
                else:
                    self.fields[field.name] = forms.CharField(
                        required=False, widget=forms.TextInput(attrs=attrs)
                    )

            elif isinstance(field, models.DateTimeField):
                self.fields[field.name] = forms.DateTimeField(
                    required=False, widget=forms.TextInput(attrs={"class": "form-control", "data-provide": "datepicker"})
                )
                self.fields[field.name] = RangeField(forms.DateTimeField,
                    required=False, widget=forms.TextInput(attrs={"class": "form-control", "data-provide": "datepicker"})
                )
    pass
"""
for field in inventory_models.Record._meta.fields:
    if isinstance(field, models.IntegerField):
        #setattr(RecordSearchForm, field.name, forms.IntegerField(required=False))
        RecordSearchForm.
"""


"""class RecordSearchForm(forms.Form):
    orbit_number_low = forms.IntegerField(required=False)
    orbit_number_high = forms.IntegerField(required=False)
    track_low = forms.IntegerField(required=False)
    track_high = forms.IntegerField(required=False)
    frame_low = forms.IntegerField(required=False)
    frame_high = forms.IntegerField(required=False)
    platform_serial_identifier = forms.CharField(required=False)
    mission_phase = forms.CharField(required=False)
    operational_mode = forms.CharField(required=False)
    swath_low = forms.IntegerField(required=False)
    swath_high = forms.IntegerField(required=False)
    product_id = forms.CharField(required=False)

    # TODO: file class / originator
    #begin_time = forms.DateTimeField()
    #end_time = forms.DateTimeField()
    insertion_time_low = forms.DateTimeField(required=False, widget=forms.SplitDateTimeWidget)
    insertion_time_high = forms.DateTimeField(required=False)
    creation_date = forms.DateTimeField(required=False)
    baseline = forms.CharField(required=False)

    # TODO: footprintCentre
    processing_centre = forms.CharField(required=False)
    processing_data_low = forms.DateTimeField(required=False)
    processing_data_high = forms.DateTimeField(required=False)
    processing_mode = forms.CharField(required=False)
    processor_version = forms.CharField(required=False)
    acquisition_station = forms.CharField(required=False)
    orbit_direction = forms.CharField(required=False)
    product_quality_degradatation_low = forms.FloatField(required=False)
    product_quality_degradatation_high = forms.FloatField(required=False)
    product_quality_status = forms.CharField(required=False)
    product_quality_degradatation_tag = forms.CharField(required=False)
"""


class TaskFilterForm(forms.Form):
    status = forms.ChoiceField(required=False, choices=((None, "All"),
                                                        ("pending", "Pending"),
                                                        ("running", "Running"),
                                                        ("finished", "Finished"),
                                                        ("failed", "Failed")),
                               widget=forms.Select(attrs={"class": "form-control"}))
