import itertools
import urllib2
from urlparse import urljoin
from contextlib import closing
import logging
import xml.etree.ElementTree as ET
import os
from os.path import join, isfile, splitext, basename
import shutil
import zipfile
import re

from django.utils.datastructures import SortedDict
from django.utils.timezone import now

from minv.inventory import models
from minv.inventory.ingest import ingest
from minv.utils import Timer, safe_makedirs
from minv.tasks.registry import task
from minv.tasks.api import schedule

logger = logging.getLogger(__name__)


class HarvestingError(Exception):
    pass


class RetrieveError(Exception):
    pass


@task
def harvest(mission, file_type, url, reschedule=False):
    """ Performs the harvesting for the specified collection and location.
    Returns
    """
    collection = models.Collection.objects.get(
        mission=mission, file_type=file_type
    )
    with collection.get_lock():
        return _harvest_locked(collection, url, reschedule)


def _harvest_locked(collection, url, reschedule):
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
    logger.debug("Scanning location %s." % location)
    available_index_files = harvester.scan()
    logger.debug("Successfully scanned location %s." % location)

    # categorize files
    inserted, updated, deleted = select_index_files(
        (base for base, url in available_index_files),
        location.index_files.values_list("filename", flat=True)
    )

    # directories for index files
    pending_dir = join(collection.data_dir, "pending", location.slug)
    ingested_dir = join(collection.data_dir, "ingested", location.slug)

    safe_makedirs(pending_dir)
    safe_makedirs(ingested_dir)

    failed_retrieve = []

    # perform actual harvesting
    for index_file_name in itertools.chain(inserted, updated):
        try:
            harvester.retrieve(
                join(url, index_file_name), index_file_name, pending_dir
            )
            logger.debug("Retrieved %s." % index_file_name)
        except:
            failed_retrieve.append(index_file_name)
            logger.debug("Failed to retrieve %s." % index_file_name)

    for index_file_name in itertools.chain(updated, deleted):
        # delete model
        location.index_files.get(filename=index_file_name).delete()
        # remove ingested index file
        os.remove(join(ingested_dir, index_file_name))

    failed_ingest = []

    # finally ingest the updated and newly inserted index files
    for index_file_name in itertools.chain(updated, inserted):
        try:
            index_file_name = extract_zipped_index_file(
                join(pending_dir, index_file_name)
            )

            ingest(
                collection.mission, collection.file_type, url,
                basename(index_file_name)
            )
            logger.debug("Ingested %s." % basename(index_file_name))
        except:
            failed_ingest.append(basename(index_file_name))
            logger.debug("Failed to ingest %s." % basename(index_file_name))

    logger.info("Finished harvesting for %s: %s" % (collection, location))
    if failed_retrieve:
        logger.error("Failed to retrieve %s" % ", ".join(failed_retrieve))
    if failed_ingest:
        logger.error("Failed to ingest %s" % ", ".join(failed_ingest))

    # if this was a scheduled harvest, reschedule it again
    if reschedule:
        try:
            interval = collection.configuration.harvest_interval
            schedule("harvest", now() + interval, {
                "mission": collection.mission,
                "file_type": collection.file_type,
                "url": location.url,
                "reschedule": True
            })
        except Exception as exc:
            logger.error(
                "Failed to reschedule harvest for %s %s. Error was '%s'." % (
                    collection, location, exc
                )
            )

    return failed_retrieve, failed_ingest


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

    return index_files_inserted, index_files_updated, index_files_deleted


CHUNK_SIZE = 64*1024  # 64kB block size


def extract_zipped_index_file(src_file):
    """ Extract a index file from a zip-archive if zipped or pass the index
    file unchanged if not zipped.
    """
    dst_file, ext = splitext(src_file)
    if ext == ".zip":
        logger.debug("Extracting zip-file %s ...", src_file)
        # NOTE: Avoid possible filesystem-to-filesystem copy.
        #       ans store the file directly in the destination folder.
        tmp_file = dst_file + ".tmp"
        timer = Timer()
        try:
            with closing(zipfile.ZipFile(src_file)) as archive:
                fin = archive.open(basename(dst_file))
                with open(tmp_file, "wb") as fout:
                    shutil.copyfileobj(fin, fout, CHUNK_SIZE)
                    size = fout.tell()
            os.rename(tmp_file, dst_file)
        except Exception as exc:
            logger.error("Extraction of %s failed: %s", src_file, exc)
            raise
        else:
            os.remove(src_file)
        finally:
            if isfile(tmp_file):
                os.remove(tmp_file)
        logger.info(
            "'%s' -> '%s' %dB %.3fs", src_file, dst_file, size, timer.stop()
        )
        return dst_file
    else:
        return src_file


class BaseHarvester(object):
    def __init__(self, location, timeout=None):
        self.location = location
        self.timeout = timeout

    def scan(self):
        pass

    def retrieve(self, url, file_name, target_dir):
        pass

# index file naming convention
RE_INDEX_PATTERN = r"\d{8,8}-\d{6,6}_\d{8,8}-\d{6,6}_\d{8,8}-\d{6,6}.index"
RE_INDEX = re.compile("^%s$" % RE_INDEX_PATTERN)
RE_INDEX_FILE = re.compile(r"^%s(?:\.zip)?$" % RE_INDEX_PATTERN)


class OADSHarvester(BaseHarvester):
    def scan(self):
        try:
            url = self.location.url
            with closing(urllib2.urlopen(url, timeout=self.timeout)) as handle:
                logger.debug("Scanning: Got response from: %s", handle.geturl())
                index_files = [
                    idx_file
                    for idx_file in extract_index_hrefs(handle, handle.geturl())
                    if RE_INDEX_FILE.match(idx_file[0])
                ]
        except Exception as exc:
            logger.error("Error parsing %s: %s", url, exc)
            raise

        # TODO: filter
        return index_files

    def retrieve(self, url, file_name, target_dir):
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
            raise RetrieveError(str(exc))
        except Exception as exc:
            logger.error("Error retrieving %s: %s", url, exc)
            raise
        finally:
            if isfile(tmp_path):
                os.remove(tmp_path)
        logger.info("'%s' -> '%s' %dB %.3fs", url, path, size, timer.stop())
        return file_name


class NGAHarvester(BaseHarvester):
    def scan(self):
        try:
            url = self.location.url
            with closing(urllib2.urlopen(url, timeout=self.timeout)) as handle:
                logger.debug("Scanning: Got response from: %s", handle.geturl())
                index_files = [
                    idx_file
                    for idx_file in extract_index_hrefs(handle, handle.geturl())
                    if RE_INDEX_FILE.match(idx_file[0])
                ]
        except Exception as exc:
            logger.error("Error parsing %s: %s", url, exc)
            raise

        # TODO: filter
        return index_files

    def retrieve(self, url, file_name, target_dir):
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
            raise RetrieveError(str(exc))
        except Exception as exc:
            logger.error("Error retrieving %s: %s", url, exc)
            raise
        finally:
            if isfile(tmp_path):
                os.remove(tmp_path)
        logger.info("'%s' -> '%s' %dB %.3fs", url, path, size, timer.stop())
        return file_name


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
