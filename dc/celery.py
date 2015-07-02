from __future__ import absolute_import
from datetime import timedelta

from celery import Celery

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
            'schedule': timedelta(minutes=2)
        },
        'calculate_user_topic_statistic': {
            'task': 'dc.tasks.calculate_user_topic_statistic',
            'schedule': timedelta(minutes=10)
        }
    }
)

if __name__ == '__main__':
    app.start()
