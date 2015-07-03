from __future__ import absolute_import
from flask import Flask
import json
import os
from dc.celery import app
from datetime import date, timedelta
from .models import init_models

flask_app = Flask(__name__)
flask_app.config.update(
    ROOT_TOPIC_ID=8,
    DEFAULT_PARENT_TOPIC_ID=26,
    CDN_HOST="http://hustlzp.qiniudn.com"
)

mode = os.environ.get('MODE')
if mode == 'PRODUCTION':
    flask_app.config.update(
        SQLALCHEMY_BINDS={
            'dc': "mysql+pymysql://root:sBLkMvu1PlRuZEAEerqa@10.80.183.93:3306/dianchang"
        }
    )
else:
    flask_app.config.update(
        SQLALCHEMY_BINDS={
            'dc': "mysql+pymysql://root:@localhost/dianchang"
        }
    )

init_models(flask_app)


@app.task
def count():
    from .models import db, Topic

    with flask_app.app_context():
        for topic in Topic.query:
            topic.all_questions_count = topic.all_questions.count()
            topic.questions_count = topic.questions.count()
            db.session.add(topic)
            db.session.commit()


@app.task
def calculate_user_topic_statistic():
    from .models import db, UserTopicStatistic, Answer, Question, Topic, UpvoteAnswer

    with flask_app.app_context():
        for topic_statistic in UserTopicStatistic.query:
            topic_id = topic_statistic.topic_id
            user_id = topic_statistic.user_id
            answers_count = []
            upvotes_count = []
            today = date.today()

            for i in xrange(0, 7):
                target_day = today - timedelta(days=i)
                answer_count = Answer.query. \
                    filter(Answer.user_id == user_id,
                           Answer.question.has(Question.topics.any(Topic.id == topic_id)),
                           db.func.date(Answer.created_at) == target_day).count()
                answers_count.insert(0, answer_count)

                upvote_count = UpvoteAnswer.query. \
                    filter(UpvoteAnswer.user_id == user_id,
                           UpvoteAnswer.answer.has(Answer.question.has(Question.topics.any(Topic.id == topic_id))),
                           db.func.date(UpvoteAnswer.created_at) == target_day).count()
                upvotes_count.insert(0, upvote_count)

                topic_statistic.week_answers_count = json.dumps(answers_count)
                topic_statistic.week_upvotes_count = json.dumps(upvotes_count)
                topic_statistic.calculate_week_score()
                db.session.add(topic_statistic)

            db.session.commit()
