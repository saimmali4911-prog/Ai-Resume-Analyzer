import json
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

def utcnow():
    return datetime.now(timezone.utc)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False, index=True)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(150), default='')
    last_name = db.Column(db.String(150), default='')
    created = db.Column(db.DateTime, default=utcnow)

    resumes = db.relationship('Resume', backref='user', lazy=True, cascade='all, delete-orphan')
    profile = db.relationship('Profile', uselist=False, backref='user', cascade='all, delete-orphan')

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

    def to_dict(self, include_profile=False):
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name or '',
            'last_name': self.last_name or '',
            'created': self.created.isoformat() if self.created else None,
        }
        if include_profile:
            data['profile'] = self.profile.to_dict() if self.profile else None
        return data


class Profile(db.Model):
    __tablename__ = 'profiles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    phone = db.Column(db.String(30), default='')
    target_role = db.Column(db.String(100), default='')
    bio = db.Column(db.Text, default='')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'phone': self.phone or '',
            'target_role': self.target_role or '',
            'bio': self.bio or ''
        }


class Resume(db.Model):
    __tablename__ = 'resumes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    text = db.Column(db.Text, default='')
    created = db.Column(db.DateTime, default=utcnow)

    analyses = db.relationship('ResumeAnalysis', backref='resume', lazy=True, cascade='all, delete-orphan')
    ats_analyses = db.relationship('ATSAnalysis', backref='resume', lazy=True, cascade='all, delete-orphan')
    matches = db.relationship('JobMatch', backref='resume', lazy=True, cascade='all, delete-orphan')
    improvements = db.relationship('Improvement', backref='resume', lazy=True, cascade='all, delete-orphan')

    @property
    def word_count(self):
        return len(self.text.split()) if self.text else 0

    def to_dict(self, include_text=False):
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'word_count': self.word_count,
            'created': self.created.isoformat() if self.created else None,
        }
        if include_text:
            data['text'] = self.text or ''
        return data


class ResumeAnalysis(db.Model):
    __tablename__ = 'resume_analyses'
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False, index=True)
    score = db.Column(db.SmallInteger)
    _data = db.Column('data', db.Text, default='{}')
    created = db.Column(db.DateTime, default=utcnow)

    @property
    def data(self):
        return json.loads(self._data or '{}')

    @data.setter
    def data(self, v):
        self._data = json.dumps(v)

    def to_dict(self):
        return {
            'id': self.id,
            'kind': 'analysis',
            'resume_id': self.resume_id,
            'score': self.score,
            'data': self.data,
            'created': self.created.isoformat() if self.created else None,
        }


class ATSAnalysis(db.Model):
    __tablename__ = 'ats_analyses'
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False, index=True)
    score = db.Column(db.SmallInteger)
    _data = db.Column('data', db.Text, default='{}')
    created = db.Column(db.DateTime, default=utcnow)

    @property
    def data(self):
        return json.loads(self._data or '{}')

    @data.setter
    def data(self, v):
        self._data = json.dumps(v)

    def to_dict(self):
        return {
            'id': self.id,
            'kind': 'ats',
            'resume_id': self.resume_id,
            'score': self.score,
            'data': self.data,
            'created': self.created.isoformat() if self.created else None,
        }


class JobMatch(db.Model):
    __tablename__ = 'job_matches'
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False, index=True)
    score = db.Column(db.SmallInteger)
    job_title = db.Column(db.String(150), default='')
    job_description = db.Column(db.Text, default='')
    _data = db.Column('data', db.Text, default='{}')
    created = db.Column(db.DateTime, default=utcnow)

    @property
    def data(self):
        return json.loads(self._data or '{}')

    @data.setter
    def data(self, v):
        self._data = json.dumps(v)

    def to_dict(self):
        return {
            'id': self.id,
            'kind': 'match',
            'resume_id': self.resume_id,
            'score': self.score,
            'job_title': self.job_title,
            'job_description': self.job_description,
            'data': self.data,
            'created': self.created.isoformat() if self.created else None,
        }


class Improvement(db.Model):
    __tablename__ = 'improvements'
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False, index=True)
    score = db.Column(db.SmallInteger, nullable=True)
    section = db.Column(db.String(60), default='')
    original = db.Column(db.Text, default='')
    _data = db.Column('data', db.Text, default='{}')
    created = db.Column(db.DateTime, default=utcnow)

    @property
    def data(self):
        return json.loads(self._data or '{}')

    @data.setter
    def data(self, v):
        self._data = json.dumps(v)

    def to_dict(self):
        return {
            'id': self.id,
            'kind': 'improve',
            'resume_id': self.resume_id,
            'score': self.score,
            'section': self.section,
            'original': self.original,
            'data': self.data,
            'created': self.created.isoformat() if self.created else None,
        }
