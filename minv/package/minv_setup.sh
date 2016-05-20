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
