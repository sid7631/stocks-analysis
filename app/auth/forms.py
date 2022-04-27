# Import Form and RecaptchaField (optional)
from flask_wtf import FlaskForm # , RecaptchaField

# Import Form elements such as TextField and BooleanField (optional)
from wtforms import StringField, PasswordField # BooleanField

# Import Form validators
from wtforms.validators import  Email, EqualTo, InputRequired


# Define the login form (WTForms)

class LoginForm(FlaskForm):
    email = StringField('Email Address', [Email(), InputRequired(message='Forgot your email address?')])
    password = PasswordField('Password', [ InputRequired(message='Must provide a password. ;-)')])