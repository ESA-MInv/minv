from os.path import dirname, join

from fabric.api import local, put, sudo, lcd, env, cd, run
from fabrant import vagrant

import minv


def archive(version=None):
    version = version or minv.__version__
    with lcd(dirname(__file__)):
        local(
            "git archive --format=tar --prefix=MInv-{version}/ master "
            "| gzip > MInv-{version}.tar.gz"
            "; mv MInv-{version}.tar.gz {builder_path}/build/SOURCES/".format(
                version=version, builder_path=env.builder_path
            )
        )


def build(version=None):
    version = version or minv.__version__
    with vagrant(env.builder_path):
        run("cp rpmbuild/SOURCES/MInv-{version}.tar.gz .".format(
            version=version
        ))
        run("tar -xzf MInv-{version}.tar.gz".format(version=version))
        with cd("MInv-{version}".format(version=version)):
            run("python setup.py bdist_rpm")
            run("cp dist/minv-{version}*rpm ../rpmbuild/RPMS/".format(
                version=version
            ))


def reset_db():
    sudo("dropdb template_postgis || true", user="postgres")
    sudo("dropdb minv || true", user="postgres")
    sudo("dropuser minv || true", user="postgres")

    put("minv/package/minv_install_postgresql.sh")
    sudo(
        'printf "abcdefghijklmnopq\nabcdefghijklmnopq" '
        '| sh minv_install_postgresql.sh'
    )


def deploy(uninstall=False, restart=True, version=None):
    version = version or minv.__version__
    put(join(env.builder_path, "build/RPMS/minv-%s-1.noarch.rpm" % version), "")
    if uninstall:
        sudo("yum remove -y minv")
    sudo("yum install -y minv-%s-1.noarch.rpm" % version)

    sudo(
        r"sed -i '/#password=/c\password=abcdefghijklmnopq' /etc/minv/minv.conf"
    )

    sudo("minv_setup.sh")

    sudo(
        "echo \"from django.contrib.auth.models import User; "
        "User.objects.create_superuser('admin', 'admin@admin.ad', 'admin')\" "
        "| minv shell"
    )
    if restart:
        sudo("service httpd restart")


def load_test_data():
    # create a folder for data
    # sudo("mkdir -p /var/minv_data")

    # try remove the collection before creating it anew
    sudo("minv collection -d -m Landsat5 -f SIP-SCENE || true", user="minv")

    # when no collection was there, clean up any remnants
    sudo("rm -rf /etc/minv/collections/Landsat5 || true")

    # create a new collection with locations
    sudo(
        "minv collection -c -m Landsat5 -f SIP-SCENE "
        "-o https://data.eox.at/minv/meta/Landsat5/SIP-SCENE/0/ "
        "-o https://data.eox.at/minv/meta/Landsat5/SIP-SCENE/1/ "
        "-o https://data.eox.at/minv/meta/Landsat5/SIP-SCENE/2/ ",
        user="minv"
    )

    # override collection configuration
    put(
        "test/data/Landsat5/SIP-SCENE/collection.conf",
        "/etc/minv/collections/Landsat5/SIP-SCENE/collection.conf",
        use_sudo=True, mode=0755
    )

    # harvest the locations
    sudo(
        "minv harvest -m Landsat5 -f SIP-SCENE "
        "-u https://data.eox.at/minv/meta/Landsat5/SIP-SCENE/0/ "
        "-u https://data.eox.at/minv/meta/Landsat5/SIP-SCENE/1/ "
        "-u https://data.eox.at/minv/meta/Landsat5/SIP-SCENE/2/ ",
        user="minv"
    )

    # add the data and mappings
    # put("test/data", "/var/minv_data", use_sudo=True)
    # put(
    #     "test/data/Landsat5/SIP-SCENE/mapping.json",
    #     "/etc/minv/collections/Landsat5/SIP-SCENE/mapping.json",
    #     use_sudo=True, mode=0755
    # )
    # sudo("chown -R minv:minv /var/minv_data")

    # ingest data into collection/locations
    # sudo(
    #     "minv minv_ingest -m Landsat5 -f SIP-SCENE "
    #     "-u http://oads1.pdgs.esa.int/ "
    #     "/var/minv_data/data/Landsat5/SIP-SCENE/0/"
    #     "19930101-000000_19931231-235959_20150709-145236.index",
    #     user="minv"
    # )
    # sudo(
    #     "minv minv_ingest -m Landsat5 -f SIP-SCENE "
    #     "-u http://oads2.pdgs.esa.int/ "
    #     "/var/minv_data/data/Landsat5/SIP-SCENE/1/"
    #     "19930101-000000_19931231-235959_20150709-145236.index",
    #     user="minv"
    # )
    # sudo(
    #     "minv minv_ingest -m Landsat5 -f SIP-SCENE "
    #     "-u http://nga1.pdgs.esa.int/ "
    #     "/var/minv_data/data/Landsat5/SIP-SCENE/2/"
    #     "19930101-000000_19931231-235959_20150709-145236.index",
    #     user="minv"
    # )
