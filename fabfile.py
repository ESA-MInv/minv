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


from os.path import dirname, join, basename
from glob import glob

from fabric.api import local, put, sudo, lcd, env, cd, run, settings
from fabrant import vagrant

import minv


RPMS = [
    "geos-3.3.8-2.el6.x86_64.rpm",
    "postgis-1.5.8-1.el6.x86_64.rpm",
    "proj-4.8.0-3.el6.x86_64.rpm",
    "Django-1.6.11-1.noarch.rpm",
]

YUM_DEPENDENCIES = [
    "httpd",
    "mod_wsgi",
    "python-psycopg2",
    "postgresql-server",
]

ALL_DEPENDENCIES = YUM_DEPENDENCIES + [
    "postgis",
    "proj",
    "geos",
    "Django"
]

USER_GROUPS = [
    ("minv-app-engineer", "minv_g_app_engineers"),
    ("minv-app-administrator", "minv_g_app_administrators"),
    ("minv-operator", "minv_g_operators"),
    ("minv-security-engineer", "minv_g_security_engineers"),
]


def run_script(path, user=None):
    put(path, "", mode=0755)
    sudo("sh -l ./%s" % basename(path), user=user)
    sudo("rm ./%s" % basename(path))


def archive(version=minv.__version__):
    with lcd(dirname(__file__)):
        local(
            "git archive --format=tar --prefix=MInv-{version}/ master "
            "| gzip > MInv-{version}.tar.gz"
            "; mv MInv-{version}.tar.gz {builder_path}/build/SOURCES/".format(
                version=version, builder_path=env.builder_path
            )
        )


def build(version=minv.__version__, release="1"):
    with vagrant(env.builder_path):
        run("cp rpmbuild/SOURCES/MInv-{version}.tar.gz .".format(
            version=version
        ))
        run("tar -xzf MInv-{version}.tar.gz".format(version=version))
        with cd("MInv-{version}".format(version=version)):
            run("python setup.py bdist_rpm --release %s" % release)
            run("cp dist/minv-{version}*rpm ../rpmbuild/RPMS/".format(
                version=version
            ))


def uninstall():
    try:
        sudo("dropdb template_postgis || true", user="postgres")
        sudo("dropdb minv || true", user="postgres")
        sudo("dropuser minv || true", user="postgres")
    except:
        pass

    for user, _ in USER_GROUPS:
        try:
            sudo("userdel -r %s || true" % user)
        except:
            pass

    try:
        sudo("yum remove -y %s minv" % " ".join(ALL_DEPENDENCIES))
    except:
        pass

    sudo("rm -rf /etc/minv/")
    sudo('/bin/rm -rf /var/lib/pgsql/data/*')
    sudo('/bin/rm -rf /disk/minv_tablespace/')


def reset_db():
    sudo("dropdb template_postgis || true", user="postgres")
    sudo("dropdb minv || true", user="postgres")
    sudo("dropuser minv || true", user="postgres")

    put("minv/package/minv_install_postgresql.sh")
    sudo(
        'printf "abcdefghijklmnopq\nabcdefghijklmnopq" '
        '| sh minv_install_postgresql.sh --tablespace /disk/minv_tablespace/'
    )


def upload(version=minv.__version__, release="1"):
    """ Implementation of TP-MINV-NOM-000-00 Step 1.1
    """
    version = version or minv.__version__
    put(
        join(
            env.builder_path,
            "build/RPMS/minv-%s-%s.noarch.rpm" % (version, release)
        ), ""
    )
    put("minv/package/minv_install_postgresql.sh", "")
    sudo("chmod a+x minv_install_postgresql.sh")
    with lcd(env.ink_path):
        for rpm in RPMS:
            put(rpm, "")


def install(version=minv.__version__, release="1"):
    """ Implementation of TP-MINV-NOM-000-00 Step 1.2
    """
    sudo("yum install -y %s" % " ".join(RPMS))
    sudo("yum install -y minv-%s-%s.noarch.rpm" % (version, release))
    sudo(
        'printf "abcdefghijklmnopq\nabcdefghijklmnopq" '
        '| sh minv_install_postgresql.sh --tablespace /disk/minv_tablespace/'
    )


def config():
    """ Implementation of TP-MINV-NOM-000-00 Step 1.3
    """
    sudo(
        r"sed -i '/#password=/c\password=abcdefghijklmnopq' /etc/minv/minv.conf"
    )
    sudo(
        r"sed -i '/log_level = INFO/c\log_level = DEBUG' /etc/minv/minv.conf"
    )


def setup():
    """ Implementation of TP-MINV-NOM-000-00 Step 1.4
    """
    sudo("minv_setup.sh")


def run_services():
    """ Implementation of TP-MINV-NOM-000-00 Step 1.5
    """
    for service in ("minvd", "httpd", "ntpd"):
        sudo("service %s start" % service)
        sudo("chkconfig %s on" % service)


def initialize():
    """ Implementation of TP-MINV-NOM-000-01 Steps 2 - 4
    """

    with settings(prompts={'Password: ': 'test', 'Password (again): ': 'test'}):
        for user, group in USER_GROUPS:
            sudo("useradd %s -G %s,minv -g minv -N || true" % (user, group))
            sudo("chmod g+rwx /home/%s" % user)
            sudo('minv_ createuser %s -g %s' % (user, group), user="minv")

    # upload script to create collections
    put(
        join(env.testdata_path, "scripts/initial_collections.sh"),
        "", mode=0755
    )
    sudo("cp initial_collections.sh /home/minv-app-administrator/")

    # upload collection configs
    for conf in glob(join(env.testdata_path, "configurations/*.conf")):
        put(conf, "", mode=0444, use_sudo=True)
        sudo("cp %s /home/minv-app-administrator/" % basename(conf))

    with cd("/home/minv-app-administrator/"):
        sudo("chmod a+rx . *")
        sudo(
            "sh -l ./initial_collections.sh",
            user="minv-app-administrator"
        )


def initialize_updates():
    sudo(
        "mkdir /home/minv-app-administrator/TDS4 || true",
        user="minv-app-administrator"
    )
    for conf in glob(join(env.testdata_path, "TDS4/configurations/*.conf")):
        put(conf, "", mode=0444, use_sudo=True)
        sudo("cp %s /home/minv-app-administrator/TDS4" % basename(conf))


def nominal(version=minv.__version__, release="1"):
    archive(version)
    build(version, release)
    upload(version, release)

    try:
        uninstall()
    except:
        pass
    install(version, release)
    config()
    setup()
    run_services()

    initialize()


def quick(version=minv.__version__, release="1"):
    archive()
    build(version, release)
    upload(version, release)

    # sudo("yum remove -y minv")
    sudo("yum reinstall -y minv-%s-%s.noarch.rpm" % (version, release))


def populate():
    run_script(join(env.testdata_path, "scripts/populate.sh"), "minv-operator")


def perf_setup():
    put(
        join(env.testdata_path, "TDS5/TDS5-MINV-PER-COL.conf"), "",
        mode=0444, use_sudo=True
    )

    sudo(
        "minv_ collection Perf/TenM "
        "-o https://data.eox.at/minv/meta/PERFOADS1/Perf/TenM/ "
        "-o https://data.eox.at/minv/meta/PERFOADS2/Perf/TenM/ "
        "-o https://data.eox.at/minv/meta/PERFOADS3/Perf/TenM/ "
        "-o https://data.eox.at/minv/meta/PERFOADS4/Perf/TenM/",
        user="minv"
    )
    sudo("minv_ config Perf/TenM -i TDS5-MINV-PER-COL.conf")
