from django import forms
from django.db import models
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from django.core.validators import ValidationError, RegexValidator
from django.forms.formsets import formset_factory

from minv.inventory import models as inventory_models


attrs = {"class": "form-control input-sm"}
float_attrs = {"class": "form-control input-sm", "step": "any"}
date_attrs = {
    "class": "form-control input-sm", "data-provide": "datepicker",
    "data-date-format": "yyyy-mm-dd", "data-date-week-start": "1"
}


class ClearableWidgetMixIn(object):
    def render(self, name, value, attrs=None):
        return mark_safe(
            '%s<span class="input-group-btn">'
            '<button class="btn btn-default btn-sm" type="button" '
            'role="clear-button">Clear</button>'
            '</span>' %
            super(ClearableWidgetMixIn, self).render(name, value, attrs)
        )


class ClearableTextInput(ClearableWidgetMixIn, forms.TextInput):
    pass


class RangeWidget(ClearableWidgetMixIn, forms.MultiWidget):
    def __init__(self, widget, *args, **kwargs):
        widgets = (widget, widget)
        super(RangeWidget, self).__init__(widgets=widgets, *args, **kwargs)

    def decompress(self, value):
        return value or []

    def format_output(self, rendered_widgets):
        return '%s<span class="input-group-addon">to</span>%s' % (
            rendered_widgets[0], rendered_widgets[1]
        )


class RangeField(forms.MultiValueField):
    default_error_messages = {
        'invalid_start': _(u'Enter a valid start value.'),
        'invalid_end': _(u'Enter a valid end value.'),
    }

    def __init__(self, field_class, widget=forms.TextInput, *args, **kwargs):
        if 'initial' not in kwargs:
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


class BBoxWidget(forms.MultiWidget):
    def __init__(self, widget, *args, **kwargs):
        widgets = (widget, widget, widget, widget)
        super(BBoxWidget, self).__init__(widgets=widgets, *args, **kwargs)

    def decompress(self, value):
        return value or []

    def format_output(self, rendered_widgets):
        widgets = rendered_widgets
        return (
            '<div data-map="%s"></div><div class="input-group">%s%s</div>' % (
                "",
                '<span class="input-group-addon">-</span>'.join(widgets),
                '<span class="input-group-btn">'
                '<button class="btn btn-default btn-sm" type="button" '
                'role="clear-button">Clear</button>'
                '</span>'
            )
        )


class BBoxField(forms.MultiValueField):
    def __init__(self, field_class, widget=forms.TextInput, *args, **kwargs):
        if 'initial' not in kwargs:
            kwargs['initial'] = ['', '', '', '']

        fields = (field_class(), field_class(), field_class(), field_class())

        super(BBoxField, self).__init__(
            fields=fields,
            widget=BBoxWidget(widget),
            *args, **kwargs
        )

    def compress(self, data_list):
        if data_list:
            cleaned = [
                field.clean(data) for field, data in zip(self.fields, data_list)
            ]

            minlat, minlon, maxlat, maxlon = cleaned

            if all(v is None for v in cleaned):
                return None

            elif any(v is None for v in cleaned):
                raise ValidationError("Not all BBox values set.")

            if minlat > maxlat:
                raise ValidationError(
                    "Minimum latitude value is higher than maximum latitude "
                    "value."
                )
            if minlon > maxlon:
                raise ValidationError(
                    "Minimum longitude value is higher than maximum longitude "
                    "value."
                )

            return cleaned

        return None


class BackupForm(forms.Form):
    backup_type = forms.ChoiceField(
        choices=(
            ("full", "full"), ("incremental", "incremental"),
            ("decremental", "decremental")
        ),
        widget=forms.Select(attrs=attrs)
    )
    subject = forms.MultipleChoiceField(
        choices=(
            ("application", "application"), ("configuration", "configuration"),
            ("logfiles", "logfiles")
        ),
        widget=forms.CheckboxSelectMultiple
    )


class RestoreForm(forms.Form):
    backup = forms.ChoiceField(
        choices=(
            ("backup_20150906.dat", "backup_20150906.dat (full)"),
            ("backup_20150907.dat", "backup_20150907.dat (incremental)"),
            ("backup_20150908.dat", "backup_20150908.dat (incremental)"),
            ("backup_20150909.dat", "backup_20150909.dat (incremental)"),
            ("backup_20150910.dat", "backup_20150910.dat (decremental)"),
            ("backup_20150911.dat", "backup_20150911.dat (full)"),
            ("backup_20150912.dat", "backup_20150912.dat (incremental)"),
        ),
        widget=forms.Select(attrs=attrs)
    )


class PaginationForm(forms.Form):
    page = forms.IntegerField(required=False, widget=forms.HiddenInput())
    records_per_page = forms.ChoiceField(
        required=False, choices=((5, "5"), (10, "10"), (15, "15"), (20, "20")),
        widget=forms.Select(attrs=attrs)
    )


class RecordSearchForm(forms.Form):
    def __init__(self, locations, *args, **kwargs):
        """ Dynamically create form fields for eligible model fields.
        """
        super(RecordSearchForm, self).__init__(*args, **kwargs)
        self.fields["locations"] = forms.MultipleChoiceField(
            required=False,
            choices=[(location.id, str(location)) for location in locations],
            widget=forms.CheckboxSelectMultiple
        )
        self.fields["area"] = BBoxField(
            forms.FloatField, required=False,
            widget=forms.NumberInput(attrs=float_attrs)
        )
        for field in inventory_models.Record._meta.fields:
            if isinstance(field, models.IntegerField):
                self.fields[field.name] = RangeField(
                    forms.IntegerField, widget=forms.NumberInput(attrs=attrs),
                    required=False
                )
            elif isinstance(field, models.FloatField):
                self.fields[field.name] = RangeField(
                    forms.FloatField,
                    widget=forms.NumberInput(attrs=float_attrs),
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
                        required=False, widget=ClearableTextInput(attrs=attrs)
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
        widget=ClearableTextInput(attrs=attrs),
        validators=[RegexValidator(DURATION_REGEX)]
    )
    export_interval = forms.CharField(required=False,
        widget=ClearableTextInput(attrs=attrs),
        validators=[RegexValidator(DURATION_REGEX)]
    )


class MetadataFieldMappingForm(forms.Form):
    index_file_key = forms.CharField()
    search_key = forms.ChoiceField(choices=inventory_models.SEARCH_FIELD_CHOICES)


MetadataMappingFormset = formset_factory(
    MetadataFieldMappingForm, can_delete=True
)


class TaskFilterForm(forms.Form):
    status = forms.ChoiceField(
        required=False,
        choices=(("", "All"), ("pending", "Pending"), ("running", "Running"),
                 ("finished", "Finished"), ("failed", "Failed"),
                 ("aborted", "Aborted")),
        widget=forms.Select(
            attrs={"class": "form-control"}
        )
    )


class TaskActionForm(forms.Form):
    action = forms.ChoiceField(
        choices=(
            ("restart", "Restart"), ("abort", "Abort"), ("remove", "Remove")
        ),
        widget=forms.Select(
            attrs={"class": "form-control"}
        )
    )
