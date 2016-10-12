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


from minv import config
from minv.utils import parse_duration

from django.utils.datastructures import SortedDict


class CollectionConfigurationReader(config.Reader):
    config.section("inventory")
    export_interval = config.Option(type=parse_duration)
    harvest_interval = config.Option(type=parse_duration)
    available_result_list_fields = config.Option(default=None, separator=",")
    available_alignment_fields = config.Option(default=None, separator=",")

    default_metadata_mapping = config.SectionOption("metadata_mapping")


def check_collection_configuration(reader):
    """ Test a collection config for validity. Returns a list or errors
    encountered.
    """
    from minv.inventory import models

    errors = []

    try:
        reader.harvest_interval
    except:
        errors.append("Invalid inventory.harvest_interval setting.")

    try:
        reader.export_interval
    except:
        errors.append("Invalid inventory.export_interval setting.")

    search_fields = set(choice[0] for choice in models.SEARCH_FIELD_CHOICES)
    alignment_fields = set(
        choice[0] for choice in models.ALIGNMENT_FIELD_CHOICES
    )

    available_result_list_fields = set(
        reader.available_result_list_fields or []
    )
    available_alignment_fields = set(
        reader.available_alignment_fields or []
    )

    if not available_result_list_fields <= search_fields:
        errors.append(
            "Invalid inventory.available_alignment_fields entries: %s"
            % ", ".join(available_alignment_fields - alignment_fields)
        )

    if not available_alignment_fields <= alignment_fields:
        errors.append(
            "Invalid inventory.available_alignment_fields entries: %s"
            % ", ".join(available_alignment_fields - alignment_fields)
        )

    mapping_sections = [
        section for section in reader._config.sections()
        if section.startswith("metadata_mapping")
    ]
    for section in mapping_sections:
        mapping_fields = set(reader.default_metadata_mapping.keys())

        if not mapping_fields <= search_fields:
            errors.append(
                "Invalid [%s] entries: %s"
                % (section, ", ".join(mapping_fields - search_fields))
            )

    return errors


def collection_configuration_changes(old, new):
    changes = SortedDict()
    if old.export_interval != new.export_interval:
        changes["inventory.export_interval"] = (
            old.export_interval, new.export_interval
        )
    if old.harvest_interval != new.harvest_interval:
        changes["inventory.harvest_interval"] = (
            old.harvest_interval, new.harvest_interval
        )
    if old.available_result_list_fields != new.available_result_list_fields:
        changes["inventory.available_result_list_fields"] = (
            old.available_result_list_fields, new.available_result_list_fields
        )
    if old.available_alignment_fields != new.available_alignment_fields:
        changes["inventory.available_alignment_fields"] = (
            old.available_alignment_fields, new.available_alignment_fields
        )

    old_mapping_sections = set(
        section for section in old._config.sections()
        if section.startswith("metadata_mapping")
    )

    new_mapping_sections = set(
        section for section in old._config.sections()
        if section.startswith("metadata_mapping")
    )

    for section in (old_mapping_sections - new_mapping_sections):
        changes[section] = (old.get_section_dict(section), None)

    for section in (new_mapping_sections - old_mapping_sections):
        changes[section] = (None, new.get_section_dict(section))

    for section in (old_mapping_sections & new_mapping_sections):
        old_mapping = old.get_section_dict(section)
        new_mapping = new.get_section_dict(section)
        for key, value in old_mapping.items():
            new_value = new_mapping.get(key)
            if value != new_value:
                changes["metadata_mapping.%s" % key] = (
                    value, new_value
                )

        for key, value in new_mapping.items():
            if key not in old_mapping:
                changes["metadata_mapping.%s" % key] = (
                    None, value
                )

    return changes
