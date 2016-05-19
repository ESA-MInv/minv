from minv import config
from minv.utils import parse_duration


class CollectionConfigurationReader(config.Reader):
    config.section("inventory")
    export_interval = config.Option(type=parse_duration)
    harvest_interval = config.Option(type=parse_duration)
    available_result_list_fields = config.Option(default=None, separator=",")
    available_alignment_fields = config.Option(default=None, separator=",")

    metadata_mapping = config.SectionOption()
