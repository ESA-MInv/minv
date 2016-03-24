python /srv/minv/manage.py minv_collection -c -m Landsat5 -f SIP-SCENE -o http://oads1.pdgs.esa.int/ -o http://oads2.pdgs.esa.int/ -n http://nga1.pdgs.esa.int/ -n http://nga2.pdgs.esa.int/
python /srv/minv/manage.py minv_ingest -m Landsat5 -f SIP-SCENE -u http://oads1.pdgs.esa.int/ /var/minv/test/data/Landsat5/SIP-SCENE/0/19930101-000000_19931231-235959_20150709-145236.index --traceback
python /srv/minv/manage.py minv_ingest -m Landsat5 -f SIP-SCENE -u http://oads2.pdgs.esa.int/ /var/minv/test/data/Landsat5/SIP-SCENE/1/19930101-000000_19931231-235959_20150709-145236.index --traceback
python /srv/minv/manage.py minv_ingest -m Landsat5 -f SIP-SCENE -u http://nga1.pdgs.esa.int/ /var/minv/test/data/Landsat5/SIP-SCENE/2/19930101-000000_19931231-235959_20150709-145236.index --traceback
