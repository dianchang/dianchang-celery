# coding: utf-8
from datetime import datetime
from ._base import db


class Question(db.Model):
    """问题"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    desc = db.Column(db.Text)
    clicks = db.Column(db.Integer, default=0)
    anonymous = db.Column(db.Boolean, default=False)  # 匿名提问
    created_at = db.Column(db.DateTime, default=datetime.now)

    answers_count = db.Column(db.Integer, default=0)
    comments_count = db.Column(db.Integer, default=0)
    followers_count = db.Column(db.Integer, default=0)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('questions',
                                                      lazy='dynamic',
                                                      order_by='desc(Question.created_at)'))

    def __repr__(self):
        return '<Question %s>' % self.name


class QuestionTopic(db.Model):
    """问题所属的话题"""
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    question_id = db.Column(db.Integer, db.ForeignKey('question.id'))
    question = db.relationship('Question', backref=db.backref('topics',
                                                              lazy='dynamic',
                                                              order_by='asc(QuestionTopic.created_at)'))

    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'))
    topic = db.relationship('Topic', backref=db.backref('questions',
                                                        lazy='dynamic',
                                                        order_by='desc(QuestionTopic.created_at)'))

    def __repr__(self):
        return '<QuestionTopic %s>' % self.id


class FollowQuestion(db.Model):
    """关注问题"""
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    question_id = db.Column(db.Integer, db.ForeignKey('question.id'))
    question = db.relationship('Question', backref=db.backref('followers',
                                                              lazy='dynamic',
                                                              order_by='desc(FollowQuestion.created_at)'))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('followed_questions',
                                                      lazy='dynamic',
                                                      order_by='desc(FollowQuestion.created_at)'))

    def __repr__(self):
        return '<FollowQuestion %s>' % self.id


class QuestionComment(db.Model):
    """对问题的评论"""
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)

    question_id = db.Column(db.Integer, db.ForeignKey('question.id'))
    question = db.relationship('Question', backref=db.backref('comments',
                                                              lazy='dynamic',
                                                              order_by='desc(QuestionComment.created_at)'))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('question_comments',
                                                      lazy='dynamic',
                                                      order_by='desc(QuestionComment.created_at)'))

    def __repr__(self):
        return '<QuestionComment %s>' % self.id


class InviteAnswer(db.Model):
    """邀请回答"""
    id = db.Column(db.Integer, primary_key=True)
    ignore = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # 被邀请者
    user = db.relationship('User', foreign_keys=[user_id])

    inviter_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # 邀请者
    inviter = db.relationship('User', foreign_keys=[inviter_id])

    question_id = db.Column(db.Integer, db.ForeignKey('question.id'))
    question = db.relationship('Question', backref=db.backref('invites',
                                                              lazy='dynamic',
                                                              order_by='desc(InviteAnswer.created_at)'))


class RejectInvitationFromUser(db.Model):
    """拒绝来自某用户的邀请"""
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    reject_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # 被拒绝用户


class RejectInvitationFromTopic(db.Model):
    """拒绝某话题下的邀请"""
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'))


class NotGoodAtTopic(db.Model):
    """不擅长某话题

    即该话题下的问题不会出现在撰写页。
    """
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'))
