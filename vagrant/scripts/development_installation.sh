cd /var/minv

pip install --editable .

# Prepare DB
python /srv/minv/manage.py syncdb --noinput --traceback

# Create admin user
python /srv/minv/manage.py shell 1>/dev/null 2>&1 <<EOF
from django.contrib.auth import authenticate
from django.contrib.auth.models import User

if authenticate(username='admin', password='admin') is None:
    user = User.objects.create_user('admin', 'admin@admin.ad', 'admin')
    user.is_superuser = True
    user.is_staff = True
    user.save()
EOF

python /srv/minv/manage.py collectstatic --noinput
