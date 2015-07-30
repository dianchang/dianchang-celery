# coding: utf-8
from __future__ import absolute_import
import logging
from datetime import timedelta
from celery import Celery
from celery.schedules import crontab
from raven import Client
from raven.contrib.celery import register_signal, register_logger_signal
from config import load_config

app = Celery('dc',
             broker='redis://localhost:6379/0',
             backend='redis://localhost:6379/0',
             include=['dc.tasks'])

# Optional configuration, see the application user guide.
app.conf.update(
    CELERY_TASK_RESULT_EXPIRES=3600,
    CELERY_TIMEZONE='Asia/Shanghai',
    CELERYBEAT_SCHEDULE={
        'count': {
            'task': 'dc.tasks.count',
            'schedule': timedelta(minutes=10)
        },
        'calculate_user_topic_statistic': {
            'task': 'dc.tasks.calculate_user_topic_statistic',
            'schedule': timedelta(minutes=10)
        },
        'relevant_topics': {
            'task': 'dc.tasks.relevant_topics',
            'schedule': timedelta(minutes=10)
        },
        'calculate_hot_topics': {
            'task': 'dc.tasks.calculate_hot_topics',
            'schedule': crontab()
        },
        'calculate_fantastic_answers': {
            'task': 'dc.tasks.calculate_fantastic_answers',
            'schedule': timedelta(minutes=2)
        }
    }
)

# 注册 Sentry
config = load_config()
if config.SENTRY_DNS:
    client = Client(dsn=config.SENTRY_DNS)
    register_logger_signal(client)
    register_signal(client)
    register_logger_signal(client, loglevel=logging.INFO)

if __name__ == '__main__':
    app.start()
