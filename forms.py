from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, EmailField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from models import User

class LoginForm(FlaskForm):
    username = StringField('Username', [DataRequired()])
    password = PasswordField('Password', [DataRequired()])

class RegisterForm(FlaskForm):
    username = StringField('Username', [DataRequired(), Length(3, 150)])
    email = EmailField('Email', [DataRequired(), Email()])
    password1 = PasswordField('Password', [DataRequired(), Length(8)])
    password2 = PasswordField('Confirm Password', [DataRequired(), EqualTo('password1', message='Passwords must match.')])

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already taken.')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError('This email is already registered.')

class UserForm(FlaskForm):
    first_name = StringField('First Name')
    last_name = StringField('Last Name')
    email = EmailField('Email', [DataRequired(), Email()])

class ProfileForm(FlaskForm):
    phone = StringField('Phone')
    target_role = StringField('Target Role')
    bio = TextAreaField('Bio')
