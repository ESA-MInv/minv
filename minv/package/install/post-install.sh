DATA_DIR=/srv/minv
CONF_DIR=/etc/minv
LOG_DIR=/var/log/minv
INSTALL_DIR=$(dirname `python -c "import minv; print(minv.__file__)"`)

mkdir -p $CONF_DIR/collections
chown -R minv:minv $CONF_DIR/collections
mkdir -p $LOG_DIR
mkdir -p $LOG_DIR/collections
touch $LOG_DIR/minv.log
chmod 0750 $LOG_DIR
chown -R minv:minv $LOG_DIR
mkdir -p /var/lock/minv/
chown -R minv:minv /var/lock/minv/
mkdir -p $DATA_DIR/collections
chown minv:minv $DATA_DIR/collections
chmod 0755 $DATA_DIR/collections

django-admin.py startproject minv_instance $DATA_DIR --template $INSTALL_DIR/instance_template
chown minv:minv -R $DATA_DIR/minv_instance
chmod 0755 $DATA_DIR/minv_instance/

python $DATA_DIR/manage.py collectstatic
