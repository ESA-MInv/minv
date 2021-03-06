# python /srv/minv/manage.py minv_collection -c -m Landsat5 -f SIP-SCENE -o http://oads1.pdgs.esa.int/ -o http://oads2.pdgs.esa.int/ -n http://nga1.pdgs.esa.int/ -n http://nga2.pdgs.esa.int/
# python /srv/minv/manage.py minv_ingest -m Landsat5 -f SIP-SCENE -u http://oads1.pdgs.esa.int/ /var/minv/test/data/Landsat5/SIP-SCENE/0/19930101-000000_19931231-235959_20150709-145236.index --traceback
# python /srv/minv/manage.py minv_ingest -m Landsat5 -f SIP-SCENE -u http://oads2.pdgs.esa.int/ /var/minv/test/data/Landsat5/SIP-SCENE/1/19930101-000000_19931231-235959_20150709-145236.index --traceback
# python /srv/minv/manage.py minv_ingest -m Landsat5 -f SIP-SCENE -u http://nga1.pdgs.esa.int/ /var/minv/test/data/Landsat5/SIP-SCENE/2/19930101-000000_19931231-235959_20150709-145236.index --traceback


python /srv/minv/manage.py collection -c Envisat/ASA_IMS_1P \
    -o https://data.eox.at/minv/meta/OADS1/Envisat/ASA_IMS_1P/ \
    -o https://data.eox.at/minv/meta/OADS2/Envisat/ASA_IMS_1P/ \
    -n https://data.eox.at/minv/meta/ngA1/Envisat/ASA_IMS_1P/ \
    -n https://data.eox.at/minv/meta/ngA2/Envisat/ASA_IMS_1P/


echo "[inventory]
export_interval = P1D
harvest_interval = P1D
available_alignment_fields = orbit_number,track,frame,instrument

[metadata_mapping]
filename = filename
# filesize =
# checksum =
orbit_number = orbitNumber
track = wrsLongitudeGrid
frame = wrsLatitudeGrid
# platform_serial_identifier =
# mission_phase =
# operational_mode =
swath = swathIdentifier
instrument = instrumentShortName
# product_id =
begin_time = beginPosition
end_time = endPosition
# insertion_time =
# creation_date =
# baseline =
# processing_centre =
# processing_date =
# processing_mode =
# processor_version =
# acquisition_station =
orbit_direction = orbitDirection
# file_type =
# product_quality_degradatation =
# product_quality_status =
# product_quality_degradatation_tag =
footprint = footprint
# scene_centre =

[metadata_mapping.https://data.eox.at/minv/meta/OADS1/Envisat/ASA_IMS_1P/]
filename = productURI
# filesize =
# checksum =
orbit_number = orbitNumber
track = wrsLongitudeGrid
frame = wrsLatitudeGrid
# platform_serial_identifier =
# mission_phase =
# operational_mode =
swath = swathIdentifier
instrument = instrumentShortName
# product_id =
begin_time = beginAcquisition
end_time = endAcquisition
# insertion_time =
# creation_date =
# baseline =
# processing_centre =
# processing_date =
# processing_mode =
# processor_version =
# acquisition_station =
orbit_direction = orbitDirection
# file_type =
# product_quality_degradatation =
# product_quality_status =
# product_quality_degradatation_tag =
footprint = footprint
# scene_centre =

[metadata_mapping.https://data.eox.at/minv/meta/OADS2/Envisat/ASA_IMS_1P/]
filename = productURI
# filesize =
# checksum =
orbit_number = orbitNumber
track = wrsLongitudeGrid
frame = wrsLatitudeGrid
# platform_serial_identifier =
# mission_phase =
# operational_mode =
swath = swathIdentifier
instrument = instrumentShortName
# product_id =
begin_time = beginAcquisition
end_time = endAcquisition
# insertion_time =
# creation_date =
# baseline =
# processing_centre =
# processing_date =
# processing_mode =
# processor_version =
# acquisition_station =
orbit_direction = orbitDirection
# file_type =
# product_quality_degradatation =
# product_quality_status =
# product_quality_degradatation_tag =
footprint = footprint
# scene_centre =
" > Envisat_ASA_IMS_1P.conf

python /srv/minv/manage.py config Envisat/ASA_IMS_1P -i Envisat_ASA_IMS_1P.conf

rm Envisat_ASA_IMS_1P.conf

python /srv/minv/manage.py harvest Envisat/ASA_IMS_1P -a
