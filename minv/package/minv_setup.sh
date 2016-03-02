DATA_DIR=/srv/minv

python $DATA_DIR/manage.py collectstatic --noinput
python $DATA_DIR/manage.py syncdb --noinput
