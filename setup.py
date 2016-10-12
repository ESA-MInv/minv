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


import os.path
from setuptools import setup, find_packages

import minv


def find_files(base_path):
    for dirpath, _, filenames in os.walk(base_path):
        for filename in filenames:
            yield os.path.join(dirpath, filename)

setup(
    name='minv',
    version=minv.__version__,
    description='MInv - Master Inventory',
    author='Fabian Schindler',
    author_email='fabian.schindler@eox.at',
    url='',
    packages=find_packages(),
    scripts=[
        "minv/package/scripts/minv_",
        "minv/package/minv_setup.sh"
    ],
    include_package_data=True,
    package_data={
        '': [
            "*.html", "*.css", "*.js", "*.eot", "*.svg",
            "*.woff", "*.woff2", "*.ttf"
        ]
    },
    data_files=[
        ("/etc/httpd/conf.d", ["minv/package/httpd_conf.d/minv.conf"]),
        ("/etc/minv", ["minv/package/minv.conf"]),
        ("/etc/logrotate.d/", ["minv/package/logrotate.d/minv"]),
        ("/etc/sudoers.d/", ["minv/package/sudoers.d/minv"]),
        (
            "/etc/profile.d/",
            ["minv/package/profile.d/minv.sh", "minv/package/profile.d/minv.csh"]
        ),
        ("/etc/init.d", ["minv/package/init.d/minvd"])
    ]
)
