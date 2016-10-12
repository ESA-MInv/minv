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


from django.test import TestCase
from django.utils.timezone import now
from django.conf import settings
from tempfile import mkdtemp
import shutil

from minv.inventory import models
from minv.inventory import queries


class InventoryMixIn(object):
    def setUp(self):
        try:
            super(InventoryMixIn, self).setUp()
            self.install_temporary()
            self.load_data()
        except:
            self.destroy_temporary()
            raise

    def tearDown(self):
        super(InventoryMixIn, self).tearDown()
        self.destroy_temporary()

    def load_data(self):
        pass

    def install_temporary(self):
        settings.MINV_CONFIG_DIR = mkdtemp()
        settings.MINV_DATA_DIR = mkdtemp()

    def destroy_temporary(self):
        shutil.rmtree(settings.MINV_CONFIG_DIR)
        shutil.rmtree(settings.MINV_DATA_DIR)


class AlignmentTestCase(InventoryMixIn, TestCase):
    def load_data(self):
        # set up collection and locations
        collection = models.Collection.objects.create(
            mission="Landsat5", file_type="SIP-SCENE"
        )
        locations = [
            models.Location.objects.create(
                collection=collection, url="http://test_%s.com" % i,
                location_type="nga" if i % 2 else "oads"
            )
            for i in range(4)
        ]
        index_files = [
            models.IndexFile.objects.create(
                location=locations[i], filename="test",
                begin_time=now(), end_time=now(), update_time=now()
            )
            for i in range(4)
        ]

        # record A is available on all locations
        models.Record.objects.create(
            location=locations[0], index_file=index_files[0],
            filename="A", checksum="A", filesize=1
        )
        models.Record.objects.create(
            location=locations[1], index_file=index_files[1],
            filename="A", checksum="A", filesize=1
        )
        models.Record.objects.create(
            location=locations[2], index_file=index_files[2],
            filename="A", checksum="A", filesize=1
        )
        models.Record.objects.create(
            location=locations[3], index_file=index_files[3],
            filename="A", checksum="A", filesize=1
        )

        # record B is only available in a subset of all locations
        models.Record.objects.create(
            location=locations[0], index_file=index_files[0],
            filename="B", checksum="A", filesize=1
        )
        models.Record.objects.create(
            location=locations[1], index_file=index_files[1],
            filename="B", checksum="A", filesize=1
        )

        models.Record.objects.create(
            location=locations[2], index_file=index_files[2],
            filename="C", checksum="C", filesize=1
        )
        models.Record.objects.create(
            location=locations[3], index_file=index_files[3],
            filename="C", checksum="C", filesize=1
        )

    def test_simple(self):
        results = queries.alignment(
            models.Collection.objects.get(
                mission="Landsat5", file_type="SIP-SCENE"
            )
        )
        print results
