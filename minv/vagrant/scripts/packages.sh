yum install -y postgresql python-psycopg2 python-pip
yum install -y httpd mod_wsgi

chkconfig httpd on
service httpd start

# Python dependencies
pip install "django<1.7" django_extensions
