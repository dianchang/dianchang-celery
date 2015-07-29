# coding: utf-8
from __future__ import absolute_import
from flask import Flask
from math import sqrt
from datetime import datetime, timedelta
import json
import os
import operator
from dc.celery import app
from datetime import date, timedelta
from .models import init_models
from .models import db, Topic, Question, Answer, UserTopicStatistic, UpvoteAnswer, RelevantTopic, QuestionTopic

flask_app = Flask(__name__)
flask_app.config.update(
    ROOT_TOPIC_ID=2,
    PRODUCT_TOPIC_ID=3,
    ORGANIZATION_TOPIC_ID=4,
    POSITION_TOPIC_ID=5,
    SKILL_TOPIC_ID=6,
    PEOPLE_TOPIC_ID=7,
    OTHER_TOPIC_ID=8,
    NC_TOPIC_ID=9,
    CDN_HOST="http://hustlzp.qiniudn.com",
    DC_DOMAIN="http://www.dianchang.me"
)

mode = os.environ.get('MODE')
if mode == 'PRODUCTION':
    flask_app.config.update(
        SQLALCHEMY_BINDS={
            'dc': "mysql+pymysql://root:dianchang2015kejizi@209.9.106.250:3306/dianchang"
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
    with flask_app.app_context():
        for topic in Topic.query:
            topic.all_questions_count = topic.all_questions.count()
            topic.questions_count = topic.questions.count()
            db.session.add(topic)
            db.session.commit()


@app.task
def calculate_user_topic_statistic():
    """计算用户在话题下的统计数据"""
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
    with flask_app.app_context():
        for topic in Topic.query:
            map(db.session.delete, topic.relevant_topics)

            relevant_topics = {}
            for question in topic.questions:
                for _topic in question.question.topics.filter(QuestionTopic.topic_id != topic.id):
                    if _topic.topic.merge_to_topic_id:
                        continue
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


@app.task
def calculate_hot_topics():
    """计算热议话题"""
    with flask_app.app_context():
        for topic in Topic.query:
            # 过去一分钟内该话题下的新问题
            new_questions_count = topic.questions.filter(
                Question.created_at >= (datetime.now() - timedelta(minutes=1))).count()

            # 过去一分钟内该话题下的新回答
            new_answers_count = topic.answers.filter(
                Answer.created_at >= (datetime.now() - timedelta(minutes=1))).count()

            current_value = new_questions_count + new_answers_count

            faz = FazScore(0.8, topic.avg, topic.sqrt_avg)
            topic.hot_score = faz.score(current_value)

            faz.update(current_value)
            topic.avg = faz.avg
            topic.sqrt_avg = faz.sqrt_avg

            db.session.add(topic)
        db.session.commit()


@app.task
def calculate_fantastic_answers():
    """计算精彩回答"""
    with flask_app.app_context():
        for answer in Answer.query.filter(~Answer.anonymous, ~Answer.hide):
            if answer.upvotes_count >= 1:
                answer.fantastic = True
                db.session.add(answer)
        db.session.commit()


class FazScore(object):
    """
    计算标准分数，见：

    http://stackoverflow.com/questions/787496/what-is-the-best-way-to-compute-trending-topics-or-tags
    """

    def __init__(self, decay, avg, sqrt_avg):
        self.decay = decay
        self.avg = avg
        self.sqrt_avg = sqrt_avg

    def update(self, value):
        # Set initial averages to the first value in the sequence.
        if self.avg == 0 and self.sqrt_avg == 0:
            self.avg = float(value)
            self.sqrt_avg = float((value ** 2))
        # Calculate the average of the rest of the values using a
        # floating average.
        else:
            self.avg = self.avg * self.decay + value * (1 - self.decay)
            self.sqrt_avg = self.sqrt_avg * self.decay + (value ** 2) * (1 - self.decay)
        return self

    def std(self):
        # Somewhat ad-hoc standard deviation calculation.
        return sqrt(self.sqrt_avg - self.avg ** 2)

    def score(self, obs):
        if self.std() == 0:
            return obs - self.avg
        else:
            return (obs - self.avg) / self.std()
