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
