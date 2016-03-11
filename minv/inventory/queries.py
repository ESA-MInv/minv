from django.utils.datastructures import SortedDict

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
    filter_locations = filters.pop("locations", None)
    qs = search(collection, filters)

    result = AlignmentResult()

    locations_qs = collection.locations.order_by("pk")
    if filter_locations:
        locations_qs = locations_qs.filter(pk__in=filter_locations)
    locations = list(locations_qs)

    for location in locations:
        current_qs = qs.filter(location=location)
        other_locations = [l for l in locations if l is not location]

        current_qs = qs.filter(location__in=other_locations).exclude(
            filename__in=qs.filter(
                location=location
            ).values_list("filename", flat=True)
        ).order_by("filename").values_list("filename", flat=True)

        # TODO: add missalignments based on checksum!

        result[location] = current_qs
    return result


class AlignmentResult(SortedDict):
    def iter_missalignments(self):
        # set up dicts for fast access
        next_filenames = SortedDict((location, None) for location in self.keys())
        iters = dict((location, iter(qs)) for location, qs in self.items())

        while True:
            for location, filename in next_filenames.items():
                if filename is None:
                    try:
                        next_filenames[location] = next(iters[location])
                    except StopIteration:
                        next_filenames[location] = None

            print next_filenames
            # select lowest id or stop if none is left
            filenames = next_filenames.values()
            try:
                lowest = min(f for f in filenames if f is not None)
            except ValueError:
                break

            # print lowest, [
            #     (record if record and record.filename == lowest else None)
            #     for record in records
            # ]

            yield lowest, [
                models.Record.objects.get(filename=lowest, location=location)
                if filename != lowest else None
                for location, filename in next_filenames.items()
            ]

            # pop next values
            for key, filename in next_filenames.items():
                if filename and filename == lowest:
                    next_filenames[key] = None
