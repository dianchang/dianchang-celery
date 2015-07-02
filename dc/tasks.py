from __future__ import absolute_import

from dc.celery import app


@app.task
def count():
    from .models import db, User, Topic

    for topic in Topic.query:
        topic.all_questions_count = topic.all_questions.count()
        topic.questions_count = topic.questions.count()
        db.session.add(topic)
        db.session.commit()
