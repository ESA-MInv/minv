from os.path import dirname, join

from fabric.api import local, put, sudo, lcd, env

import minv


def deploy(uninstall=False, restart=True, version=None):
    version = version or minv.__version__
    put(join(env.builder_path, "build/RPMS/minv-%s-1.noarch.rpm" % version), "")
    if uninstall:
        sudo("yum remove -y minv")
    sudo("yum install -y minv-%s-1.noarch.rpm" % version)
    if restart:
        sudo("service httpd restart")


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

    with lcd(env.builder_path):
        local("vagrant up")
        local("vagrant ssh -c '%s'" % " ; ".join([
            "rm -rf MInv-{version}",
            "cp rpmbuild/SOURCES/MInv-{version}.tar.gz .",
            "tar -xzf MInv-{version}.tar.gz",
            "cd MInv-{version}",
            "python setup.py bdist_rpm",
            "cp dist/minv-{version}*rpm ../rpmbuild/RPMS/"
        ]).format(version=version))
