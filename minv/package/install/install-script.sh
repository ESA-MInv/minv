# this seems to be the default install directive
python setup.py install --single-version-externally-managed -O1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

CONFIGFILES="\
%config(noreplace) /etc/httpd/conf.d/minv.conf
%config(noreplace) /etc/logrotate.d/minv
%config(noreplace) /etc/minv/minv.conf"

sed -i '/\/etc\/httpd\/conf.d\/minv.conf/d' INSTALLED_FILES
sed -i '/\/etc\/logrotate.d\/minv/d' INSTALLED_FILES
sed -i '/\/etc\/minv\/minv.conf/d' INSTALLED_FILES

echo "$CONFIGFILES" | cat INSTALLED_FILES - > INSTALLED_FILES.new

mv INSTALLED_FILES.new INSTALLED_FILES

