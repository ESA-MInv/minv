printf "abcdefghijklmnopq\nabcdefghijklmnopq" | sh /var/minv/minv/package/minv_install_postgresql.sh


# adding privileges for testing
sudo -u postgres psql -q -c "ALTER USER minv SUPERUSER NOCREATEROLE CREATEDB;"

# adding access restrictions for test DB
awk '/local   minv minv md5/ { print; print "local   test_minv minv md5"; next }1' /var/lib/pgsql/data/pg_hba.conf > tmp && mv tmp /var/lib/pgsql/data/pg_hba.conf
