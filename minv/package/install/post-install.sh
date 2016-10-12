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


DATA_DIR=/srv/minv
CONF_DIR=/etc/minv
LOG_DIR=/var/log/minv
INSTALL_DIR=$(dirname `python -c "import minv; print(minv.__file__)"`)

mkdir -p $CONF_DIR/collections
chmod 0770 $CONF_DIR/collections
chown minv:minv $CONF_DIR/minv.conf
chown minv:minv -R $CONF_DIR

mkdir -p $LOG_DIR
mkdir -p $LOG_DIR/collections
touch $LOG_DIR/minv.log
touch $LOG_DIR/django.log
chmod g+w $LOG_DIR/minv.log
chmod g+w $LOG_DIR/django.log
chmod 0770 $LOG_DIR
chown minv:minv -R $LOG_DIR

mkdir -p /var/lock/minv/
chown minv:minv -R /var/lock/minv/

mkdir -p /tmp/minv/daemon/
chown minv:minv -R /tmp/minv

mkdir -p $DATA_DIR/collections
chown minv:minv $DATA_DIR/collections
chmod 0770 $DATA_DIR/collections

django-admin.py startproject minv_instance $DATA_DIR --template $INSTALL_DIR/instance_template
chown minv:minv -R $DATA_DIR/minv_instance
chmod 0771 $DATA_DIR/minv_instance/
