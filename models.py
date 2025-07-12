
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import desc

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user', nullable=False)  # guest, user, admin
    is_banned = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    questions = db.relationship('Question', backref='author', lazy=True, cascade='all, delete-orphan')
    answers = db.relationship('Answer', backref='author', lazy=True, cascade='all, delete-orphan')
    votes = db.relationship('Vote', backref='voter', lazy=True, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password, password)
    
    def get_unread_notifications(self):
        return Notification.query.filter_by(user_id=self.id, seen=False).count()
    
    def get_recent_notifications(self, limit=10):
        return Notification.query.filter_by(user_id=self.id).order_by(desc(Notification.timestamp)).limit(limit).all()

    def __repr__(self):
        return f'<User {self.username}>'

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)  # HTML content from Quill
    tags = db.Column(db.String(500))  # comma-separated tags
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    views = db.Column(db.Integer, default=0)
    
    # Relationships
    answers = db.relationship('Answer', backref='question', lazy=True, cascade='all, delete-orphan')
    
    def get_tags_list(self):
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()] if self.tags else []
    
    def get_accepted_answer(self):
        return Answer.query.filter_by(question_id=self.id, is_accepted=True).first()
    
    def get_answer_count(self):
        return Answer.query.filter_by(question_id=self.id).count()

    def __repr__(self):
        return f'<Question {self.title}>'

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)  # HTML content from Quill
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    votes = db.Column(db.Integer, default=0)
    is_accepted = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    vote_records = db.relationship('Vote', backref='answer', lazy=True, cascade='all, delete-orphan')
    
    def get_user_vote(self, user_id):
        return Vote.query.filter_by(answer_id=self.id, user_id=user_id).first()

    def __repr__(self):
        return f'<Answer {self.id} for Question {self.question_id}>'

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    answer_id = db.Column(db.Integer, db.ForeignKey('answer.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    vote_type = db.Column(db.Integer, nullable=False)  # 1 for upvote, -1 for downvote
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Ensure a user can only vote once per answer
    __table_args__ = (db.UniqueConstraint('answer_id', 'user_id', name='unique_vote_per_answer'),)

    def __repr__(self):
        return f'<Vote {self.vote_type} by User {self.user_id} on Answer {self.answer_id}>'

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    seen = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Notification {self.id} for User {self.user_id}>'
