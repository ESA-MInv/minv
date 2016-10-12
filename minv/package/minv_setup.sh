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

python $DATA_DIR/manage.py collectstatic --noinput
python $DATA_DIR/manage.py syncdb --noinput

python $DATA_DIR/manage.py shell 1>/dev/null 2>&1 <<EOF
from django.contrib.auth.models import Group, Permission

group_permissions = {
    "minv_g_app_engineers": ["can_configure_collections", "can_export"],
    "minv_g_app_administrators": ["can_configure_collections", "can_export"],
    "minv_g_operators": [],
    "minv_g_security_engineers": ["can_backup"],
}

for name, permissions in group_permissions.items():
    group, _ = Group.objects.get_or_create(name=name)
    for permission in permissions:
        group.permissions.add(
            Permission.objects.get(
                codename=permission, content_type__app_label='inventory'
            )
        )
    group.save()

EOF
