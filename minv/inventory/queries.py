from minv.inventory import models


def search(collection, filters=None):
    """
    """
    qs = models.Record.objects.filter(location__collection=collection)
    if filters:
        for key, value in filters.items():
            if value is None or value == "":
                continue
            if key == "locations":
                if not value:
                    continue
                filter_ = {"location__in": value}
            elif isinstance(value, list):
                if len(value) == 2:
                    low, high = value
                    if key == "acquisition_date":
                        key_low = "begin_date"
                        key_high = "end_date"
                    else:
                        key_low = key
                        key_high = key

                    filter_ = {
                        "%s__lte" % key_low: high, "%s__gte" % key_high: low
                    }
                else:
                    # TODO implement area filtering
                    filter_ = {}

            else:
                filter_ = {key: value}

            qs = qs.filter(**filter_)

    return qs


def alignment(collection, filters=None):
    """ This function performs the alignment check with the given parameters.
    """

    qs = search(collection, filters)

    # TODO:
    #

    result = []
    locations = list(collection.locations.all())

    for location in locations:
        current_qs = qs.filter(location=location)
        # exclusion_qs = qs.filter(location=location)
        other_locations = (l for l in locations if l is not location)

        current_qs = qs.filter(location__in=other_locations).exclude(
            filename__in=qs.filter(
                location=location
            ).values_list("filename", flat=True)
        )


        # for other_location in other_locations:
        #     excludes = qs.filter(
        #         location=other_location
        #     ).values_list("filename", flat=True)
        #     current_qs = current_qs.exclude(filename__in=excludes)

        result.append((location, current_qs))
    return result
