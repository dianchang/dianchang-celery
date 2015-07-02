# coding: utf-8
from datetime import datetime
from flask import current_app
from ._base import db


class Topic(db.Model):
    """话题"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    name_pinyin = db.Column(db.String(100))
    wiki = db.Column(db.Text(4294967295))
    wiki_preview = db.Column(db.Text)
    avatar = db.Column(db.String(200), default='default.png')
    clicks = db.Column(db.Integer, default=0)
    root = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    locked = db.Column(db.Boolean, default=False)  # 话题锁定，无法删除话题、合并话题
    name_locked = db.Column(db.Boolean, default=False)
    desc_locked = db.Column(db.Boolean, default=False)
    wiki_locked = db.Column(db.Boolean, default=False)
    avatar_locked = db.Column(db.Boolean, default=False)
    parent_topics_locked = db.Column(db.Boolean, default=False)
    child_topics_locked = db.Column(db.Boolean, default=False)

    followers_count = db.Column(db.Integer, default=0)
    questions_count = db.Column(db.Integer, default=0)  # 问题数量
    all_questions_count = db.Column(db.Integer, default=0)  # 问题数量（包含子话题下的问题）

    @property
    def ancestor_paths(self):
        """寻找跟话题到该话题之间的所有路径"""
        ROOT_TOPIC_ID = current_app.config.get('ROOT_TOPIC_ID')
        ancestor_topics_id_list = self.ancestor_topics_id_list[:]
        all_list = ancestor_topics_id_list[:]
        all_list.append(self.id)

        nodes = {}
        for ancestor_topic_id in ancestor_topics_id_list:
            ancestor_topic = Topic.query.get_or_404(ancestor_topic_id)
            child_topics_id_list = ancestor_topic.child_topics_id_list
            nodes[ancestor_topic_id] = _intersect_list(child_topics_id_list, all_list)
        paths = Topic.find_all_paths(nodes, ROOT_TOPIC_ID, self.id)

        topic_paths = []
        for path in paths:
            topic_path = Topic.query.filter(Topic.id.in_(path))
            print(topic_path)
            topic_paths.append(topic_path)
        return topic_paths

    @property
    def all_questions(self):
        """该话题下的所有问题（包括子话题的问题）"""
        from .question import QuestionTopic, Question

        topics_id_list = self.descendant_topics_id_list
        topics_id_list.append(self.id)
        return Question.query.filter(Question.topics.any(QuestionTopic.topic_id.in_(
            topics_id_list))).order_by(Question.created_at.desc())

    @property
    def all_answers(self):
        """该话题下的所有问题回答（包括子话题的问题回答）"""
        from .answer import Answer
        from .question import Question, QuestionTopic

        topics_id_list = self.descendant_topics_id_list
        topics_id_list.append(self.id)
        return Answer.query.filter(Answer.question.has(Question.topics.any(
            QuestionTopic.topic_id.in_(topics_id_list))))

    @property
    def parent_topics(self):
        """直接父话题"""
        parent_topics_id_list = db.session.query(TopicClosure.ancestor_id). \
            filter(TopicClosure.descendant_id == self.id,
                   TopicClosure.ancestor_id != self.id,
                   TopicClosure.path_length == 1). \
            all()
        parent_topics_id_list = [item.ancestor_id for item in parent_topics_id_list]
        return Topic.query.filter(Topic.id.in_(parent_topics_id_list))

    @property
    def ancestor_topics_id_list(self):
        """祖先话题id列表"""
        ancestor_topics_id_list = db.session.query(TopicClosure.ancestor_id). \
            filter(TopicClosure.descendant_id == self.id,
                   TopicClosure.ancestor_id != self.id). \
            all()
        return [item.ancestor_id for item in ancestor_topics_id_list]

    @property
    def ancestor_topics(self):
        """祖先话题"""
        return Topic.query.filter(Topic.id.in_(self.ancestor_topics_id_list))

    @property
    def child_topics_id_list(self):
        """直接子话题id列表"""
        child_topics_id_list = db.session.query(TopicClosure.descendant_id). \
            filter(TopicClosure.ancestor_id == self.id,
                   TopicClosure.descendant_id != self.id,
                   TopicClosure.path_length == 1). \
            all()
        return [item.descendant_id for item in child_topics_id_list]

    @property
    def child_topics(self):
        """直接子话题"""
        return Topic.query.filter(Topic.id.in_(self.child_topics_id_list))

    @property
    def descendant_topics_id_list(self):
        """子孙话题id列表"""
        descendant_topics_id_list = db.session.query(TopicClosure.descendant_id). \
            filter(TopicClosure.ancestor_id == self.id,
                   TopicClosure.descendant_id != self.id).all()
        return [item.descendant_id for item in descendant_topics_id_list]

    @property
    def descendant_topics(self):
        """子孙话题"""
        return Topic.query.filter(Topic.id.in_(self.descendant_topics_id_list))

    def add_parent_topic(self, parent_topic_id):
        """添加直接父话题"""
        for ancestor_topic in TopicClosure.query.filter(TopicClosure.descendant_id == parent_topic_id):
            for descendant_topic in TopicClosure.query.filter(TopicClosure.ancestor_id == self.id):
                closure = TopicClosure.query. \
                    filter(TopicClosure.ancestor_id == ancestor_topic.ancestor_id,
                           TopicClosure.descendant_id == descendant_topic.descendant_id).first()
                if not closure:
                    new_closure = TopicClosure(ancestor_id=ancestor_topic.ancestor_id,
                                               descendant_id=descendant_topic.descendant_id,
                                               path_length=ancestor_topic.path_length + descendant_topic.path_length + 1)
                    db.session.add(new_closure)
        db.session.commit()

    def remove_parent_topic(self, parent_topic_id):
        """删除直接父话题"""
        for ancestor_topic in TopicClosure.query.filter(TopicClosure.descendant_id == parent_topic_id):
            for descendant_topic in TopicClosure.query.filter(TopicClosure.ancestor_id == self.id):
                closure = TopicClosure.query.filter(TopicClosure.ancestor_id == ancestor_topic.ancestor_id,
                                                    TopicClosure.descendant_id == descendant_topic.descendant_id)
                map(db.session.delete, closure)
        db.session.commit()

    def add_child_topic(self, child_topic_id):
        """添加直接子话题"""
        for ancestor_topic in TopicClosure.query.filter(TopicClosure.descendant_id == self.id):
            for descendant_topic in TopicClosure.query.filter(TopicClosure.ancestor_id == child_topic_id):
                closure = TopicClosure.query. \
                    filter(TopicClosure.ancestor_id == ancestor_topic.ancestor_id,
                           TopicClosure.descendant_id == descendant_topic.descendant_id).first()
                if not closure:
                    new_closure = TopicClosure(ancestor_id=ancestor_topic.ancestor_id,
                                               descendant_id=descendant_topic.descendant_id,
                                               path_length=ancestor_topic.path_length + descendant_topic.path_length + 1)
                    db.session.add(new_closure)
        db.session.commit()

    def remove_child_topic(self, child_topic_id):
        """删除直接子话题"""
        for ancestor_topic in TopicClosure.query.filter(TopicClosure.descendant_id == self.id):
            for descendant_topic in TopicClosure.query.filter(TopicClosure.ancestor_id == child_topic_id):
                closure = TopicClosure.query.filter(TopicClosure.ancestor_id == ancestor_topic.ancestor_id,
                                                    TopicClosure.descendant_id == descendant_topic.descendant_id)
                map(db.session.delete, closure)
        db.session.commit()

    @staticmethod
    def find_all_paths(graph, start, end, path=[]):
        """获取图中节点A到节点B的所有路径"""
        path = path + [start]
        if start == end:
            return [path]
        if not graph.has_key(start):
            return []
        paths = []
        for node in graph[start]:
            if node not in path:
                newpaths = Topic.find_all_paths(graph, node, end, path)
                for newpath in newpaths:
                    paths.append(newpath)
        return paths

    def __repr__(self):
        return '<Topic %s>' % self.name


class TopicClosure(db.Model):
    """话题的closure table"""
    id = db.Column(db.Integer, primary_key=True)
    ancestor_id = db.Column(db.Integer, db.ForeignKey('topic.id'))
    descendant_id = db.Column(db.Integer, db.ForeignKey('topic.id'))
    path_length = db.Column(db.Integer)

    def __repr__(self):
        return '<TopicClosure %d-%d>' % (self.ancestor_id, self.descendant_id)


class FollowTopic(db.Model):
    """关注话题"""
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'))
    topic = db.relationship('Topic', backref=db.backref('followers',
                                                        lazy='dynamic',
                                                        order_by='desc(FollowTopic.created_at)'))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('followed_topics',
                                                      lazy='dynamic',
                                                      order_by='desc(FollowTopic.created_at)'))

    def __repr__(self):
        return '<FollowQuestion %s>' % self.id


class TopicWikiContributor(db.Model):
    """话题Wiki贡献者"""
    id = db.Column(db.Integer, primary_key=True)
    count = db.Column(db.Integer, default=0)
    last_contributed_at = db.Column(db.DateTime, default=datetime.now)
    created_at = db.Column(db.DateTime, default=datetime.now)

    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'))
    topic = db.relationship('Topic', backref=db.backref('wiki_contributors',
                                                        lazy='dynamic',
                                                        order_by='desc(TopicWikiContributor.count)'))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('contributed_topics',
                                                      lazy='dynamic',
                                                      order_by='desc(TopicWikiContributor.count)'))


class UserTopicStatistic(db.Model):
    """话题统计

    记录用户在某话题下的数据。
    """
    id = db.Column(db.Integer, primary_key=True)
    answers_count = db.Column(db.Integer, default=0)  # 用户在该话题下的回答数
    upvotes_count = db.Column(db.Integer, default=0)  # 用户在该话题下收获的赞同数
    score = db.Column(db.Integer, default=0)  # 用户对该话题的擅长度
    selected = db.Column(db.Boolean, default=False)  # 是否选择该话题作为擅长话题
    show_order = db.Column(db.Integer, default=0)  # 擅长话题排列顺序（越大越排在后面）
    experience = db.Column(db.String(200))  # 话题经验
    week_answers_count = db.Column(db.String(200))  # 近7天的回答数，以数组的 json 形式存入，例如：[1,2,3,4,5,6,7]，越往左天数越早
    week_upvotes_count = db.Column(db.String(200))  # 近7天的赞同数，格式同上
    week_score = db.Column(db.Float, default=0)  # 近7天的表现得分
    created_at = db.Column(db.DateTime, default=datetime.now)

    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'))
    topic = db.relationship('Topic')

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User')

    @staticmethod
    def add_answer_in_topic(user_id, topic_id):
        """在某话题下回答"""
        topic_expert = UserTopicStatistic.query.filter(
            UserTopicStatistic.topic_id == topic_id,
            UserTopicStatistic.user_id == user_id).first()
        if topic_expert:
            topic_expert.answers_count += 1
        else:
            topic_expert = UserTopicStatistic(topic_id=topic_id, user_id=user_id, answers_count=1, upvotes_count=0)
        topic_expert.calculate_score()
        db.session.add(topic_expert)
        db.session.commit()

    @staticmethod
    def remove_answer_from_topic(user_id, topic_id):
        """从某话题中移除回答"""
        topic_expert = UserTopicStatistic.query.filter(UserTopicStatistic.topic_id == topic_id,
                                                       UserTopicStatistic.user_id == user_id).first()
        if topic_expert:
            if topic_expert.answers_count > 0:
                topic_expert.answers_count -= 1
            else:
                topic_expert.answers_count = 0
        else:
            topic_expert = UserTopicStatistic(topic_id=topic_id, user_id=user_id, answers_count=0, upvotes_count=0)
        topic_expert.calculate_score()
        db.session.add(topic_expert)
        db.session.commit()

    @staticmethod
    def upvote_answer_in_topic(user_id, topic_id, count=1):
        """在该话题下赞同该用户"""
        topic_expert = UserTopicStatistic.query.filter(UserTopicStatistic.topic_id == topic_id,
                                                       UserTopicStatistic.user_id == user_id).first()
        if topic_expert:
            topic_expert.upvotes_count += count
        else:
            topic_expert = UserTopicStatistic(topic_id=topic_id, user_id=user_id, upvotes_count=count, answers_count=0)
        topic_expert.calculate_score()
        db.session.add(topic_expert)
        db.session.commit()

    @staticmethod
    def cancel_upvote_answer_in_topic(user_id, topic_id, count=1):
        """取消在该话题下对该用户的赞同"""
        topic_expert = UserTopicStatistic.query.filter(UserTopicStatistic.topic_id == topic_id,
                                                       UserTopicStatistic.user_id == user_id).first()
        if topic_expert:
            if topic_expert.upvotes_count >= count:
                topic_expert.upvotes_count -= count
            else:
                topic_expert.upvotes_count = 0
        else:
            topic_expert = UserTopicStatistic(topic_id=topic_id, user_id=user_id, answers_count=0, upvotes_count=0)
        topic_expert.calculate_score()
        db.session.add(topic_expert)
        db.session.commit()

    def calculate_score(self):
        """计算擅长度"""
        self.score = self.answers_count + self.upvotes_count

    def calculate_week_score(self):
        """计算近7天的得分"""
        # TODO
        pass


class ApplyTopicDeletion(db.Model):
    """申请删除话题"""
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'))
    topic = db.relationship('Topic')

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User')


def _intersect_list(a, b):
    """求列表的并"""
    return list(set(a).intersection(b))
