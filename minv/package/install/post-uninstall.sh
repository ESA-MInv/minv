DATA_DIR=/srv/minv
CONF_DIR=/etc/minv
LOG_DIR=/var/log/minv

rm -rf $DATA_DIR
rm -rf /var/lock/minv/

# create groups
groupdel minv_g_app_engineers
groupdel minv_g_app_administrators
groupdel minv_g_operators
groupdel minv_g_security_engineers
