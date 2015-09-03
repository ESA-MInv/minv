from django import forms
from django.db import models
from django.utils.translation import ugettext as _
from django.core.validators import ValidationError, RegexValidator
from django.forms.formsets import formset_factory

from minv.inventory import models as inventory_models


class RangeWidget(forms.MultiWidget):
    def __init__(self, widget, *args, **kwargs):
        widgets = (widget, widget)

        super(RangeWidget, self).__init__(widgets=widgets, *args, **kwargs)

    def decompress(self, value):
        print value
        return value or []

    def format_output(self, rendered_widgets):
        return '%s<span class="input-group-addon">to</span>%s' % (
            rendered_widgets[0], rendered_widgets[1]
        )

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
            value_low = self.fields[0].clean(data_list[0])
            value_high = self.fields[1].clean(data_list[1])

            print value_low, value_high
            if value_low is not None and value_high is not None:
                if value_low > value_high:
                    raise ValidationError(
                        "Lower value is higher than higher value."
                    )
                return [value_low, value_high]
            elif value_low is not None:
                return value_low
            elif value_high is not None:
                raise ValidationError("Only higher value is set.")

        return None

attrs = {"class": "form-control input-sm"}
date_attrs = {
    "class": "form-control input-sm", "data-provide": "datepicker",
    "data-date-format": "yyyy-mm-dd", "data-date-week-start": "1"
}


class RecordSearchForm(forms.Form):
    records_per_page = forms.ChoiceField(
        required=False, choices=((5, "5"), (10, "10"), (15, "15"), (20, "20")),
        widget=forms.Select(attrs=attrs)
    )
    page = forms.IntegerField(required=False, widget=forms.HiddenInput())

    def __init__(self, locations, *args, **kwargs):
        """ Dynamically create form fields for eligible model fields.
        """
        super(RecordSearchForm, self).__init__(*args, **kwargs)
        self.fields["locations"] = forms.MultipleChoiceField(
            required=False,
            choices=[(location.id, str(location)) for location in locations],
            widget=forms.CheckboxSelectMultiple
        )
        for field in inventory_models.Record._meta.fields:
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
            elif isinstance(field, models.DateTimeField):
                name = field.name
                if name == "begin_time":
                    continue
                elif name == "end_time":
                    name = "acquisition_date"
                self.fields[name] = RangeField(forms.DateTimeField,
                    required=False, widget=forms.TextInput(attrs=date_attrs)
                )
            elif isinstance(field, models.CharField):
                if field.choices:
                    self.fields[field.name] = forms.ChoiceField(
                        required=False, choices=(("", "---"),) + field.choices,
                        widget=forms.Select(attrs=attrs)
                    )
                else:
                    self.fields[field.name] = forms.CharField(
                        required=False, widget=forms.TextInput(attrs=attrs)
                    )


class ImportExportBaseForm(forms.Form):
    selection = forms.ChoiceField(required=False,
        choices=(("full", "Full: Configuration and Data"),
                 ("config", "Configuration only"),
                 ("data", "Data only")),
        widget=forms.Select(attrs={"class": "form-control"})
    )


class ImportForm(ImportExportBaseForm):
    upload_package = forms.FileField(required=False)

    def __init__(self, available_packages, *args, **kwargs):
        """ Dynamically create form fields for eligible model fields.
        """
        super(ImportForm, self).__init__(*args, **kwargs)
        self.fields["select_package"] = forms.ChoiceField(required=False,
            choices=(((None, "---"),) + available_packages),
            widget=forms.Select(attrs={"class": "form-control"})
        )

DURATION_REGEX = (
    "P(?=\w*\d)(?:\d+Y|Y)?(?:\d+M|M)?(?:\d+W|W)?(?:\d+D|D)?(?:T(?:\d+H|H)?(?:\d+M|M)?(?:\d+(?:\.\d{1,2})?S|S)?)?$"
)


class CollectionConfigurationForm(forms.Form):
    harvest_interval = forms.CharField(required=False,
        widget=forms.TextInput(attrs=attrs),
        validators=[RegexValidator(DURATION_REGEX)]
    )
    export_interval = forms.CharField(required=False,
        widget=forms.TextInput(attrs=attrs),
        validators=[RegexValidator(DURATION_REGEX)]
    )


class MetadataFieldMappingForm(forms.Form):
    index_file_key = forms.CharField()
    search_key = forms.ChoiceField(choices=inventory_models.SEARCH_FIELD_CHOICES)


MetadataMappingFormset = formset_factory(
    MetadataFieldMappingForm, can_delete=True
)


class TaskFilterForm(forms.Form):
    status = forms.ChoiceField(required=False, choices=(("", "All"),
                                                        ("pending", "Pending"),
                                                        ("running", "Running"),
                                                        ("finished", "Finished"),
                                                        ("failed", "Failed")),
                               widget=forms.Select(
                                   attrs={"class": "form-control"})
                               )
