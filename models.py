import json
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(150), default='')
    last_name = db.Column(db.String(150), default='')
    created = db.Column(db.DateTime, default=datetime.utcnow)
    resumes = db.relationship('Resume', backref='user', lazy=True, cascade='all,delete')
    profile = db.relationship('Profile', uselist=False, backref='user', cascade='all,delete')

    def set_password(self, pw): self.password_hash = generate_password_hash(pw)
    def check_password(self, pw): return check_password_hash(self.password_hash, pw)

class Profile(db.Model):
    __tablename__ = 'profiles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True)
    phone = db.Column(db.String(30), default='')
    target_role = db.Column(db.String(100), default='')
    bio = db.Column(db.Text, default='')

class Resume(db.Model):
    __tablename__ = 'resumes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    text = db.Column(db.Text, default='')
    created = db.Column(db.DateTime, default=datetime.utcnow)
    analyses = db.relationship('ResumeAnalysis', backref='resume', lazy=True, cascade='all,delete')
    ats_analyses = db.relationship('ATSAnalysis', backref='resume', lazy=True, cascade='all,delete')
    matches = db.relationship('JobMatch', backref='resume', lazy=True, cascade='all,delete')
    improvements = db.relationship('Improvement', backref='resume', lazy=True, cascade='all,delete')

    @property
    def word_count(self): return len(self.text.split())

class ResumeAnalysis(db.Model):
    __tablename__ = 'resume_analyses'
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'))
    score = db.Column(db.SmallInteger)
    _data = db.Column('data', db.Text, default='{}')
    created = db.Column(db.DateTime, default=datetime.utcnow)
    @property
    def data(self): return json.loads(self._data or '{}')
    @data.setter
    def data(self, v): self._data = json.dumps(v)

class ATSAnalysis(db.Model):
    __tablename__ = 'ats_analyses'
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'))
    score = db.Column(db.SmallInteger)
    _data = db.Column('data', db.Text, default='{}')
    created = db.Column(db.DateTime, default=datetime.utcnow)
    @property
    def data(self): return json.loads(self._data or '{}')
    @data.setter
    def data(self, v): self._data = json.dumps(v)

class JobMatch(db.Model):
    __tablename__ = 'job_matches'
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'))
    score = db.Column(db.SmallInteger)
    job_title = db.Column(db.String(150), default='')
    job_description = db.Column(db.Text, default='')
    _data = db.Column('data', db.Text, default='{}')
    created = db.Column(db.DateTime, default=datetime.utcnow)
    @property
    def data(self): return json.loads(self._data or '{}')
    @data.setter
    def data(self, v): self._data = json.dumps(v)

class Improvement(db.Model):
    __tablename__ = 'improvements'
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'))
    score = db.Column(db.SmallInteger, nullable=True)
    section = db.Column(db.String(60), default='')
    original = db.Column(db.Text, default='')
    _data = db.Column('data', db.Text, default='{}')
    created = db.Column(db.DateTime, default=datetime.utcnow)
    @property
    def data(self): return json.loads(self._data or '{}')
    @data.setter
    def data(self, v): self._data = json.dumps(v)
