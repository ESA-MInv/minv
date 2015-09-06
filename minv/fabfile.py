from fabric.api import local, env, put, sudo


env.hosts = ["5.9.173.45"]
env.user = "centos"


def deploy():
    local("python setup.py sdist")
    put("dist/minv-0.0.1.tar.gz", "")
    sudo("pip install minv-0.0.1.tar.gz  -U")
    sudo("service httpd restart")
