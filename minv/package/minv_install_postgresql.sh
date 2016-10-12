# ------------------------------------------------------------------------------
#
# Project: Master Inventory <http://github.com/ESA-MInv/minv>
# Authors: Fabian Schindler <fabian.schindler@eox.at>
#
# ------------------------------------------------------------------------------
# Copyright (C) 2016 European Space Agency
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies of this Software or works derived from this Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
# ------------------------------------------------------------------------------


DBNAME=minv
DBTMPL=template_postgis
DBUSER=minv
DBTABLESPACE=

usage() {
cat <<EOF
Usage: ${0##*/} [-h] [-u USER] [-d DATABASE]
Install PostgreSQL with PostGIS and create a new database and user to use 
for MInv.

    -h           display this help and exit
    -u USER      name of the database user. defaults to 'minv'
    -d DATABASE  name of the to be created database. defaults to 'minv'
    -t TEMPLATE  name of the template database. defaults to 'template_postgis'
    --tablespace set a directory to store the database files
    --drop       drop the previous user/database if they exist
EOF
}

while [[ $# > 0 ]] ; do
    key="$1"
    case $key in
        -u|--user)
            DBUSER="$2"
            shift
            ;;
        -d|--database)
            DBNAME="$2"
            shift
            ;;
        -t|--template)
            DBTMPL="$2"
            shift
            ;;
        --tablespace)
            DBTABLESPACE="$2"
            shift
            ;;
        --drop)
            DROP=YES
            ;;
        *)
            usage
            exit 1
            ;;
    esac
    shift
done

read -s -p "Enter Password: " password
echo
read -s -p "Re-Enter Password: " pw_confirm

[ "$password" == "$pw_confirm" ] || {
    echo "Entered passwords do not match."
    exit 1
}

echo "Installing PostgreSQL and PostGIS packages."
yum -y install postgresql-server postgis

service postgresql initdb
chkconfig postgresql on
service postgresql start

cd /home # to suppress warning

[ -n $DROP ] && {
    echo "Dropping databases: '$DBTMPL' and '$DBNAME' and user '$DBUSER'"
    sudo -u postgres dropdb $DBTMPL || true
    sudo -u postgres dropdb $DBNAME || true
    sudo -u postgres dropuser $DBUSER || true
}

echo "Creating template database '$DBTMPL'"
sudo -u postgres createdb $DBTMPL
sudo -u postgres createlang plpgsql $DBTMPL

PG_SHARE=/usr/share/pgsql
POSTGIS_SQL="postgis-64.sql"
[ -f "$PG_SHARE/contrib/$POSTGIS_SQL" ] || POSTGIS_SQL="postgis.sql"

echo "Installing postgis on '$DBTMPL'."
sudo -u postgres psql -q -d $DBTMPL -f "$PG_SHARE/contrib/$POSTGIS_SQL"
sudo -u postgres psql -q -d $DBTMPL -f "$PG_SHARE/contrib/spatial_ref_sys.sql"
sudo -u postgres psql -q -d $DBTMPL -c "GRANT ALL ON geometry_columns TO PUBLIC;"
sudo -u postgres psql -q -d $DBTMPL -c "GRANT ALL ON geography_columns TO PUBLIC;"
sudo -u postgres psql -q -d $DBTMPL -c "GRANT ALL ON spatial_ref_sys TO PUBLIC;"

echo "Creating DB user '$DBUSER'"
sudo -u postgres psql -q -c "CREATE USER $DBUSER WITH ENCRYPTED PASSWORD '$password' NOSUPERUSER NOCREATEDB NOCREATEROLE ;"
sudo -u postgres psql -q -c "DROP TABLESPACE IF EXISTS minv_tablespace ;"

if [ -z "$DBTABLESPACE" ] ; then
    echo "Create Database without tablespace."
    # no tablespace
    sudo -u postgres psql -q -c "CREATE DATABASE $DBNAME WITH OWNER $DBUSER TEMPLATE $DBTMPL ENCODING 'UTF-8' ;"
else
    echo "Create Database with tablespace '$DBTABLESPACE'."
    # create the tablespace itself
    mkdir -p $DBTABLESPACE
    chown postgres:postgres $DBTABLESPACE
    sudo -u postgres psql -q -c "CREATE TABLESPACE minv_tablespace LOCATION '$DBTABLESPACE' ;"

    # create the DB with the tablespace
    sudo -u postgres psql -q -c "CREATE DATABASE $DBNAME WITH OWNER $DBUSER TEMPLATE $DBTMPL ENCODING 'UTF-8' TABLESPACE minv_tablespace ;"
fi


PG_HBA="`sudo -u postgres psql -qA -d $DBTMPL -c "SHOW data_directory;" | grep -m 1 "^/"`/pg_hba.conf"

{ sudo -u postgres ex "$PG_HBA" || /bin/true ; } <<END
g/^\s*local\s*$DBNAME/d
/#\s*TYPE\s*DATABASE\s*USER\s*.*ADDRESS\s*METHOD/a
# minv instance
local   $DBNAME $DBUSER md5
local   $DBNAME all reject
.
wq
END

cd -

service postgresql restart
