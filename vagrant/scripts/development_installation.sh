cd /var/minv

pip install --editable .

sh /var/minv/minv/package/minv_setup.sh

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

# create test users

python /srv/minv/manage.py createuser minv-app-engineer –g minv_g_app_engineers
python /srv/minv/manage.py createuser minv-app-administrator -g minv_g_app_administrators
python /srv/minv/manage.py createuser minv-operator -g minv_g_operators
python /srv/minv/manage.py createuser minv-security-engineer -g minv_g_security_engineers
