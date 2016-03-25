from minv import config


class CollectionConfigurationReader(config.Reader):
    config.section("inventory")
    export_interval = config.Option(default=None)
    harvest_interval = config.Option(default=None)
    available_alignment_fields = config.Option(default=None, separator=",")

    metadata_mapping = config.SectionOption()
