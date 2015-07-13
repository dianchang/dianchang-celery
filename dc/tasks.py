# coding: utf-8
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
    """统一各模型的count类字段"""
    from .models import db, Topic

    with flask_app.app_context():
        for topic in Topic.query:
            topic.all_questions_count = topic.all_questions.count()
            topic.questions_count = topic.questions.count()
            db.session.add(topic)
            db.session.commit()


@app.task
def calculate_user_topic_statistic():
    """计算用户在话题下的统计数据"""
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


@app.task
def relevant_topics():
    """计算每个话题的相关话题"""
    import operator
    from dc.models import db, Topic, QuestionTopic, RelevantTopic

    with flask_app.app_context():
        for topic in Topic.query:
            map(db.session.delete, topic.relevant_topics)

            relevant_topics = {}
            for question in topic.questions:
                for _topic in question.question.topics.filter(QuestionTopic.topic_id != topic.id):
                    if _topic.topic_id in relevant_topics:
                        relevant_topics[_topic.topic_id] += 1
                    else:
                        relevant_topics[_topic.topic_id] = 0

            relevant_topics = sorted(relevant_topics.items(), key=operator.itemgetter(1))
            relevant_topics.reverse()
            for relevant_topic_id, score in relevant_topics:
                relevant_topic = RelevantTopic(topic_id=topic.id, relevant_topic_id=relevant_topic_id, score=score)
                db.session.add(relevant_topic)
            db.session.commit()
