from minv import config
from minv.utils import parse_duration

from django.utils.datastructures import SortedDict


class CollectionConfigurationReader(config.Reader):
    config.section("inventory")
    export_interval = config.Option(type=parse_duration)
    harvest_interval = config.Option(type=parse_duration)
    available_result_list_fields = config.Option(default=None, separator=",")
    available_alignment_fields = config.Option(default=None, separator=",")

    metadata_mapping = config.SectionOption()


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
    mapping_fields = set(reader.metadata_mapping.keys())

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

    if not mapping_fields < search_fields:
        errors.append(
            "Invalid [metadata_mapping] entries: %s"
            % ", ".join(mapping_fields - search_fields)
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

    for key, value in old.metadata_mapping.items():
        new_value = new.metadata_mapping.get(key)
        if value != new_value:
            changes["metadata_mapping.%s" % key] = (
                value, new_value
            )

    for key, value in new.metadata_mapping.items():
        if key not in old.metadata_mapping:
            changes["metadata_mapping.%s" % key] = (
                None, value
            )

    return changes
