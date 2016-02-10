yum install -y postgresql python-psycopg2 python-pip
yum install -y httpd mod_wsgi

chkconfig httpd on
service httpd start

# Python dependencies
pip install "django<1.7" django_extensions


# Restart Apache after boot hopefully after all shares are available.
if ! grep -Fxq "service httpd restart" /etc/rc.d/rc.local ; then
    cat << EOF >> /etc/rc.d/rc.local

# Restart Apache after boot hopefully after all shares are available.
sleep 15
service httpd restart
EOF
fi
