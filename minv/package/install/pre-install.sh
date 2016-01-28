# create 'minv' user and group if not existing
id -g minv >/dev/null 2>&1 || groupadd -r minv
id -u minv >/dev/null 2>&1 || {
    useradd -r -M -g minv -d /srv/minv -s /sbin/nologin -c "Master Inventory system user" minv
    usermod -L minv
}
