import itertools
import urllib2
from urlparse import urljoin
from contextlib import closing
import logging
import xml.etree.ElementTree as ET
import os
from os.path import join, isfile
import errno
import shutil

from django.utils.datastructures import SortedDict
from django.utils.text import slugify

from minv.inventory import models
from minv.inventory.ingest import ingest
from minv.utils import Timer


logger = logging.getLogger(__name__)


class HarvestingError(Exception):
    pass


def harvest(mission, file_type, url):
    collection = models.Collection.objects.get(
        mission=mission, file_type=file_type
    )
    location = collection.locations.get(url=url)

    if location.location_type == "oads":
        harvester = OADSHarvester(location)
    elif location.location_type == "nga":
        harvester = NGAHarvester(location)
    else:
        raise HarvestingError(
            "Invalid location type '%s'." % location.location_type
        )

    # scan the source
    available_index_files = harvester.scan()

    # categorize files
    inserted, updated, deleted = select_index_files(
        (base for base, url in available_index_files),
        location.index_files.values_list("filename", flat=True)
    )

    slug = slugify(unicode(url))

    # directories for index files
    pending_dir = join(collection.data_dir, "pending", slug)
    ingested_dir = join(collection.data_dir, "ingested", slug)
    failed_dir = join(collection.data_dir, "failed", slug)

    for dir_path in (pending_dir, ingested_dir, failed_dir):
        try:
            os.makedirs(dir_path)
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise

    # perform actual harvesting
    for index_file_name in itertools.chain(inserted, updated):
        harvester.retrieve(
            join(url, index_file_name), index_file_name, pending_dir
        )

    for index_file_name in itertools.chain(updated, deleted):
        # delete model
        location.index_files.get(filename=index_file_name).delete()
        # remove ingested index file
        os.remove(join(ingested_dir, index_file_name))

    for index_file_name in itertools.chain(updated, inserted):
        try:
            ingest(mission, file_type, url, join(pending_dir, index_file_name))
        except:
            os.rename(
                join(pending_dir, index_file_name),
                join(ingested_dir, index_file_name)
            )
            raise
        else:
            os.rename(
                join(pending_dir, index_file_name),
                join(failed_dir, index_file_name)
            )


def select_index_files(available_index_files, ingested_index_files):
    """ Split the supplied available index files and already ingested index
    files to three separate lists:
        - new index files that only need to be ingested
        - index files that have updates: this is a list of tuples: (old, new)
        - deleted index files
    """

    available = SortedDict(
        (index[:31], index) for index in available_index_files
    )

    ingested = SortedDict(
        (index[:31], index) for index in ingested_index_files
    )

    index_files_inserted = [
        index for base, index in available.iteritems() if base not in ingested
    ]
    print available

    index_files_deleted = [
        index for base, index in ingested.iteritems() if base not in available
    ]

    common = (
        (ingested[base], index) for base, index in available.iteritems()
        if base in ingested
    )

    index_files_updated = [
        (old, new) for old, new in common if old[32:47] < new[32:47]
    ]


    print index_files_inserted, index_files_updated, index_files_deleted
    return index_files_inserted, index_files_updated, index_files_deleted


class BaseHarvester(object):
    def __init__(self, location, timeout=None):
        self.location = location
        self.timeout = timeout

    def scan(self):
        pass

    def retrieve(self, url, file_name, target_dir):
        pass


class OADSHarvester(BaseHarvester):
    def scan(self):
        try:
            url = self.location.url
            with closing(urllib2.urlopen(url, timeout=self.timeout)) as handle:
                logger.debug("Scanning: Got response from: %s", handle.geturl())
                index_files = extract_index_hrefs(handle, handle.geturl())
        except Exception as exc:
            logger.error("Error parsing %s: %s", url, exc)
            raise

        # TODO: filter
        return index_files

    def retrieve(self, url, file_name, target_dir):

        print url, file_name, target_dir
        path = join(target_dir, file_name)
        tmp_path = path + ".tmp"
        logger.debug("Retrieving %s and storing it under %s", url, path)
        timer = Timer()
        try:
            with closing(urllib2.urlopen(url, timeout=self.timeout)) as fin:
                with open(tmp_path, "wb") as fout:
                    shutil.copyfileobj(fin, fout, 64*1024)
                    size = fout.tell()
            os.rename(tmp_path, path)
        except IOError as exc:
            logger.error("Error saving %s: %s", path, exc)
            raise Exception(str(exc))
        except Exception as exc:
            logger.error("Error retrieving %s: %s", url, exc)
            raise
        finally:
            if isfile(tmp_path):
                os.remove(tmp_path)
        logger.info("'%s' -> '%s' %dB %.3fs", url, path, size, timer.stop())
        return file_name


class NGAHarvester(BaseHarvester):
    pass


def extract_index_hrefs(source, base_url=None):
    """ Extract a list of index file names and URLs pairs from an index.html
    file. The subroutine expands the relative URLs if the `base_url` is given.
    Note that the subroutine currently does not intepret the <base> HTML
    element!
    """
    root = ET.parse(source, parser=None)
    return [
        # the ".//*/a[@class='index-file']" expression does not seem to work
        # with Python 2.6s XPath engine. Workaround:
        (el.attrib["href"].split("/")[-1], urljoin(base_url, el.attrib["href"]))
        for el in itertools.chain(
            root.findall(".//*/{http://www.w3.org/1999/xhtml}a"),
            root.findall(".//*/a"),
        ) if el.attrib.get("class") == "index-file"
    ]
