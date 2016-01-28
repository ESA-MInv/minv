DATA_DIR=/srv/minv
CONF_DIR=/etc/minv
LOG_DIR=/var/log/minv
mkdir -p $CONF_DIR/collections
chown -R minv:minv $CONF_DIR/collections
mkdir -p $LOG_DIR
mkdir -p $LOG_DIR/collections
touch $LOG_DIR/minv.log
chmod 0750 $LOG_DIR
chown -R minv:minv $LOG_DIR
#mkdir -p /var/lock/minv/
#chown -R minv:minv /var/lock/minv/
mkdir -p $DATA_DIR/collections
chown minv:minv $DATA_DIR/collections
chmod 0755 $DATA_DIR/collections
sed -ie '/WSGIDaemonProcess/s/vagrant/minv/g' /etc/httpd/conf.d/minv.conf
sed -ie '/USER=/s/vagrant/minv/g' /etc/init.d/harvestd
