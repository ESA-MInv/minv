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

    if restart:
        sudo("service httpd restart")


def reset_db():
    sudo("dropdb template_postgis", user="postgres")
    sudo("dropdb minv", user="postgres")
    sudo("dropuser minv", user="postgres")
    put("minv/package/minv_install_postgresql.sh")
    sudo(
        'printf "abcdefghijklmnopq\nabcdefghijklmnopq" '
        '| sh minv_install_postgresql.sh'
    )


def load_test_data():
    put("test/data")
    sudo(
        "minv minv_collection -c -m Landsat5 -f SIP-SCENE "
        "-o http://oads1.pdgs.esa.int/ "
        "-o http://oads2.pdgs.esa.int/ "
        "-n http://nga1.pdgs.esa.int/ "
        "-n http://nga2.pdgs.esa.int/",
        user="minv"
    )
    put(
        "test/data/Landsat5/SIP-SCENE/mapping.json",
        "/etc/minv/collections/Landsat5/SIP-SCENE/mapping.json",
        use_sudo=True
    )
    sudo(
        "minv minv_ingest -m Landsat5 -f SIP-SCENE "
        "-u http://oads1.pdgs.esa.int/ "
        "data/Landsat5/SIP-SCENE/0/19930101-000000_19931231-235959_20150709-145236.index",
        "data/Landsat5/SIP-SCENE/0/19990101-000000_19991231-235959_20150709-144402.index",
        user="minv"
    )
