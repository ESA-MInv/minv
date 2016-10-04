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


# create system groups/users

# for groupname in minv_g_app_engineers minv_g_app_administrators minv_g_operators minv_g_security_engineers
# do
#     groupadd $groupname -f
# done

groupadd minv_g_app_engineers -f
groupadd minv_g_app_administrators -f
groupadd minv_g_operators -f
groupadd minv_g_security_engineers -f

id -u minv-app-engineer > /dev/null 2> /dev/null || useradd minv-app-engineer -G minv_g_app_engineers
id -u minv-app-administrator > /dev/null 2> /dev/null || useradd minv-app-administrator -G minv_g_app_administrators
id -u minv-operator > /dev/null 2> /dev/null || useradd minv-operator -G minv_g_operators
id -u minv-security-engineer > /dev/null 2> /dev/null || useradd minv-security-engineer -G minv_g_security_engineers

# create test users

# sudo -u minv-app-administrator python /srv/minv/manage.py createuser minv-app-engineer -g minv_g_app_engineers
# sudo -u minv-app-administrator python /srv/minv/manage.py createuser minv-app-administrator -g minv_g_app_administrators
# sudo -u minv-app-administrator python /srv/minv/manage.py createuser minv-operator -g minv_g_operators
# sudo -u minv-app-administrator python /srv/minv/manage.py createuser minv-security-engineer -g minv_g_security_engineers

# create them hackily
python /srv/minv/manage.py shell 1>/dev/null 2>&1 <<EOF
from django.contrib.auth import authenticate
from django.contrib.auth.models import User

ugs = (
    ("minv-app-engineer", "minv_g_app_engineers"),
    ("minv-app-administrator", "minv_g_app_administrators"),
    ("minv-operator", "minv_g_operators"),
    ("minv-security-engineer", "minv_g_security_engineers"),
)

for username, groupname in ugs:
    try:
        user = User.objects.create_user(username, 'test')
        group = models.Group.objects.get(name=groupname)
        user.groups.add(group)
    except:
        pass

EOF