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
from django.contrib.gis.db import models
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from django.core.validators import ValidationError, RegexValidator
from django.forms.formsets import formset_factory
from django.forms.util import flatatt
from django.utils.encoding import force_text
from django.utils.html import format_html
from django.utils.datastructures import MultiValueDict, MergeDict

from minv.inventory import models as inventory_models


DURATION_REGEX = (
    "P(?=\w*\d)(?:\d+Y|Y)?(?:\d+M|M)?(?:\d+W|W)?(?:\d+D|D)?(?:T(?:\d+H|H)?"
    "(?:\d+M|M)?(?:\d+(?:\.\d{1,2})?S|S)?)?$"
)


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

# This fixes issues when rendering forms with RangeFields as_hidden


class MultipleHiddenInput(forms.HiddenInput):
    """
    A widget that handles <input type="hidden"> for fields that have a list
    of values.
    """
    def __init__(self, attrs=None, choices=()):
        super(MultipleHiddenInput, self).__init__(attrs)
        # choices can be any iterable
        self.choices = choices

    def render(self, name, value, attrs=None, choices=()):
        if value is None:
            value = []
        final_attrs = self.build_attrs(attrs, type=self.input_type, name=name)
        id_ = final_attrs.get('id', None)
        inputs = []
        for i, v in enumerate(value):
            input_attrs = dict(value=force_text(v), **final_attrs)
            if id_:
                # An ID attribute was given. Add a numeric index as a suffix
                # so that the inputs don't all have the same ID attribute.
                input_attrs['id'] = '%s_%s' % (id_, i)

            input_attrs['name'] = '%s_%s' % (input_attrs['name'], i)
            inputs.append(format_html('<input{0} />', flatatt(input_attrs)))
        return mark_safe('\n'.join(inputs))

    def value_from_datadict(self, data, files, name):
        if isinstance(data, (MultiValueDict, MergeDict)):
            return data.getlist(name)
        return data.get(name, None)


class RangeField(forms.MultiValueField):
    default_error_messages = {
        'invalid_start': _(u'Enter a valid start value.'),
        'invalid_end': _(u'Enter a valid end value.'),
    }

    hidden_widget = MultipleHiddenInput

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
    hidden_widget = MultipleHiddenInput

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


class TypeAheadWidget(forms.TextInput):
    def __init__(self, values, *args, **kwargs):
        super(TypeAheadWidget, self).__init__(*args, **kwargs)
        self.values = values

    def render(self, name, value, attrs=None):
        new_attrs = {"list": "%s_list" % name}
        new_attrs.update(attrs)
        return mark_safe("%s<datalist id='%s_list'>%s</datalist>" % (
            super(TypeAheadWidget, self).render(name, value, new_attrs),
            name, "".join("<option value='%s'>" % value for value in self.values)
        ))

################################################################################


class BackupForm(forms.Form):
    def __init__(self, available_backups, *args, **kwargs):
        super(BackupForm, self).__init__(*args, **kwargs)
        self.fields["backup_type"] = forms.ChoiceField(
            choices=(
                ("full", "full"), ("incremental", "incremental"),
                ("differential", "differential")
            ),
            widget=forms.Select(attrs=attrs)
        )
        self.fields["interval"] = forms.CharField(required=False,
            widget=ClearableTextInput(attrs=attrs),
            validators=[RegexValidator(DURATION_REGEX)]
        )
        self.fields["differential_file"] = forms.ChoiceField(
            required=False,
            choices=available_backups,
            widget=forms.Select(attrs=attrs)
        )
        self.fields["subject"] = forms.MultipleChoiceField(
            choices=(
                ("application", "application"),
                ("configuration", "configuration"),
                ("logfiles", "logfiles")
            ),
            widget=forms.CheckboxSelectMultiple
        )


class RestoreForm(forms.Form):
    def __init__(self, available_backups, *args, **kwargs):
        super(RestoreForm, self).__init__(*args, **kwargs)
        self.fields["backup"] = forms.ChoiceField(
            choices=available_backups,
            widget=forms.Select(attrs=attrs)
        )


class PaginationForm(forms.Form):
    page = forms.IntegerField(required=False, widget=forms.HiddenInput())
    records_per_page = forms.ChoiceField(
        required=False, choices=((5, "5"), (10, "10"), (15, "15"), (20, "20")),
        widget=forms.Select(attrs=attrs)
    )


def create_formfield_for_model_field(model_field):
    if isinstance(model_field, models.IntegerField):
        return RangeField(
            forms.IntegerField, widget=forms.NumberInput(attrs=attrs),
            required=False
        )
    elif isinstance(model_field, models.FloatField):
        return RangeField(
            forms.FloatField,
            widget=forms.NumberInput(attrs=float_attrs),
            required=False
        )
    elif isinstance(model_field, models.DateTimeField):
        return RangeField(forms.DateTimeField,
            required=False, widget=forms.TextInput(attrs=date_attrs)
        )
    elif isinstance(model_field, models.CharField):
        if model_field.choices:
            return forms.ChoiceField(
                required=False, choices=(("", "---"),) + model_field.choices,
                widget=forms.Select(attrs=attrs)
            )
        else:
            return forms.CharField(
                required=False, widget=ClearableTextInput(attrs=attrs)
            )

    raise ValueError("No such field %s" % model_field.name)


class SearchForm(forms.Form):
    def __init__(self, locations, available_search_fields, *args, **kwargs):
        """ Dynamically create form fields for eligible model fields.
        """
        super(SearchForm, self).__init__(*args, **kwargs)
        self.fields["locations"] = forms.MultipleChoiceField(
            required=False,
            choices=[(location.id, str(location)) for location in locations],
            widget=forms.CheckboxSelectMultiple
        )

        # area widget
        have_footprint = "footprint" in available_search_fields
        have_scene_centre = "scene_centre" in available_search_fields
        if have_footprint or have_scene_centre:
            self.fields["area"] = BBoxField(
                forms.FloatField, required=False,
                widget=forms.NumberInput(attrs=float_attrs)
            )

        if have_footprint and have_scene_centre:
            self.fields["area_footprint_or_scene_centre"] = forms.ChoiceField(
                required=False, choices=[
                    ("footprint", "Footprint"),
                    ("scene_centre", "Scene Centre")
                ],
                widget=forms.Select(attrs=attrs)
            )

        for field in inventory_models.Record._meta.fields:
            name = field.name

            # skip fields that are treated otherwise
            if name in ("id", "location", "index_file", "scene_centre",
                        "footprint"):
                continue

            # only use fields that are configured
            if name not in available_search_fields:
                continue

            if isinstance(field, models.DateTimeField):
                if name == "begin_time":
                    continue
                elif name == "end_time":
                    name = "acquisition_date"
            self.fields[name] = create_formfield_for_model_field(field)


class RecordSearchResultListForm(forms.Form):
    def __init__(self, locations, *args, **kwargs):
        super(RecordSearchResultListForm, self).__init__(*args, **kwargs)
        self.fields["result_list_location"] = forms.ChoiceField(
            required=False,
            choices=[(location.id, str(location)) for location in locations],
            widget=forms.HiddenInput()
        )

        sort_choices = []
        for field in inventory_models.SEARCH_FIELD_CHOICES:
            sort_choices.append(("-" + field[0], "-" + field[0]))
            sort_choices.append((field[0], field[0]))

        self.fields["sort"] = forms.ChoiceField(
            required=False, choices=sort_choices, widget=forms.HiddenInput()
        )


class AddAnnotationForm(forms.Form):
    def __init__(self, locations, *args, **kwargs):
        super(AddAnnotationForm, self).__init__(*args, **kwargs)
        self.fields["location"] = forms.ChoiceField(
            required=False,
            choices=[("", "-----")] + [
                (location.id, str(location)) for location in locations
            ],
            widget=forms.Select(attrs=attrs)
        )
        self.fields["text"] = forms.CharField(
            widget=forms.Textarea(attrs=attrs)
        )


class AddAnnotationListForm(forms.Form):
    add_annotations_to_all = forms.BooleanField(
        required=False, widget=forms.CheckboxInput(attrs=attrs)
    )
    do_add_annotation = forms.CharField(
        required=False, widget=forms.HiddenInput()
    )
    text = forms.CharField(required=False, widget=forms.Textarea(attrs=attrs))


class AlignmentForm(forms.Form):
    """ Form to gather parameters for the alignment check.
    """
    def __init__(self, locations, available_alignment_fields, *args, **kwargs):
        """ Dynamically create form fields for eligible model fields.
        """
        super(AlignmentForm, self).__init__(*args, **kwargs)
        self.fields["format"] = forms.ChoiceField(
            required=True,
            choices=[("html", "HTML"), ("csv", "CSV"), ("tsv", "TSV")],
            widget=forms.Select(attrs=attrs)
        )
        self.fields["locations"] = forms.MultipleChoiceField(
            required=False,
            choices=[(location.id, str(location)) for location in locations],
            widget=forms.CheckboxSelectMultiple
        )
        self.fields["instrument"] = forms.CharField(
            required=False, widget=ClearableTextInput(attrs=attrs)
        )

        for name, __ in inventory_models.ALIGNMENT_FIELD_CHOICES:
            if name in available_alignment_fields:
                self.fields[name] = create_formfield_for_model_field(
                    inventory_models.Record._meta.get_field_by_name(name)[0]
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

list_inline = dict(attrs)
list_inline["class"] = "list-inline"


class CollectionConfigurationForm(forms.Form):
    harvest_interval = forms.CharField(required=False,
        widget=ClearableTextInput(attrs=attrs),
        validators=[RegexValidator(DURATION_REGEX)]
    )
    export_interval = forms.CharField(required=False,
        widget=ClearableTextInput(attrs=attrs),
        validators=[RegexValidator(DURATION_REGEX)]
    )
    available_result_list_fields = forms.MultipleChoiceField(
        required=False,
        choices=[
            field
            for field in inventory_models.SEARCH_FIELD_CHOICES
            if field[0] not in (
                "filename", "filesize", "footprint", "scene_centre"
            )
        ],
        widget=forms.CheckboxSelectMultiple(attrs=list_inline)
    )
    available_alignment_fields = forms.MultipleChoiceField(
        required=False, choices=inventory_models.ALIGNMENT_FIELD_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs=list_inline)
    )


class MetadataFieldMappingForm(forms.Form):
    index_file_key = forms.CharField(required=False, widget=TypeAheadWidget([
        "recordLastUpdate", "beginAcquisition", "endAcquisition",
        "availabilityTime", "plattformShortName", "plattformSerialIdentifier",
        "instrumentShortName", "sensorType", "operationalMode", "resolution",
        "swathIdentifier", "orbitNumber", "orbitDirection", "wrsLongitudeGrid",
        "wrsLatitudeGrid", "startTimeFromAscendingNode",
        "completionTimeFromAscendingNode", "illuminationAzimuthAngle",
        "illuminationZenithAngle", "illuminationElevationAngle",
        "incidanceAngle", "acrossTrackIncidenceAngle",
        "alongTrackIncidenceAngle", "footprint", "sceneCentre", "productURI",
        "productVersion", "productSize", "timeliness", "productId",
        "parentIdentifier", "acquisitionType", "acquisitionSubType",
        "productType", "productQualityDegredation", "productQualityStatus",
        "productQualityDegredationTag", "productQualityReportURL",
        "productGroupId", "browseImageLocationList",
        "browseMetadataLocationList", "browseAvailabilityDateList",
        "thumbnailImageLocationList", "boundingBox", "browseColRowList",
        "cloudCoverPercentage", "snowCoverPercentage", "multiViewAngles",
        "centreViewAngles", "polarisationMode", "polarisationChannels",
        "antennaLookDirection", "minimumIncidenceAngle", "maximumIncidenceAngle",
        "incidenceAngleVariation", "dopplerFrequency", "nominalTrack",
        "occulationPoints"
        ], attrs=attrs)
    )
    search_key = forms.ChoiceField(
        choices=inventory_models.SEARCH_FIELD_CHOICES,
        widget=forms.Select(attrs=attrs)
    )


MetadataMappingFormset = formset_factory(
    MetadataFieldMappingForm, can_delete=True, extra=0
)
