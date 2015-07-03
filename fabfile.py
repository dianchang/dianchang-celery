# coding: utf-8
from fabric.api import local, run, env, cd, prefix, shell_env

host_string = "root@119.254.101.73"


def deploy():
    """部署"""
    env.host_string = host_string
    with cd('/var/www/dianchang-celery'):
        with shell_env(MODE='PRODUCTION'):
            run('git reset --hard HEAD')
            run('git pull')
            run('git pull --recurse-submodules')
            with prefix('source venv/bin/activate'):
                run('pip install -r requirements.txt')
                run('pip install -r dc/models/requirements.txt')
            run('supervisorctl restart celerybeat')
            run('supervisorctl restart celery')


def restart():
    """重启"""
    env.host_string = host_string
    run('supervisorctl restart celerybeat')
    run('supervisorctl restart celery')
