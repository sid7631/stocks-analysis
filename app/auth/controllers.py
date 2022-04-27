# Import flask dependencies
import os
from flask import Blueprint, request, render_template, flash, g, session, redirect, url_for
from flask_login import current_user, login_user

# Import password / encryption helper tools
from werkzeug.security import check_password_hash, generate_password_hash
from app.api.utils import create_folder

# Import the database object from the main app module
from app.db_config import db

# Import module forms
from app.auth.forms import LoginForm

# Import module models (i.e. User)
from app.auth.models import User

from flask import current_app as app
from flask_login import LoginManager, login_user, login_required, current_user, logout_user

# Define the blueprint: 'auth', set its url prefix: app.url/auth
auth = Blueprint('auth', __name__, url_prefix='/auth')





# Set the route and accepted methods
@auth.route('/signin/', methods=['GET', 'POST'])
def signin():

    if request.method == 'POST':
        # If sign in form is submitted
        form = LoginForm(request.form)
        remember = True if request.form.get('remember') else False

        # Verify the sign in form
        if form.validate_on_submit():

            user = User.query.filter_by(email=form.email.data).first()

            if user and check_password_hash(user.password, form.password.data):
                session['user_id'] = user.id
                login_user(user, remember=remember)
                flash('Welcome %s' % user.name)
                return redirect("/portfolio")

            flash('Wrong email or password', 'error-message')
        return render_template("auth/signin.html", form=form)
    
    if request.method == 'GET':
        if current_user.is_authenticated:
            return redirect('/portfolio')
        form = LoginForm(request.form)
        return render_template('auth/signin.html', form=form)


@auth.route("/signup/", methods=["POST", "GET"])
@auth.route("/signup", methods=["POST", "GET"])
def signup():
    if request.method == "POST":
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user: # if a user is found, we want to redirect back to signup page so user can try again
            flash('Email address already exists')
            return redirect(url_for('auth.signup'))

        new_user = User(email=email, name=name, password=generate_password_hash(password, method='sha256'))

        db.session.add(new_user)
        db.session.commit()
        create_folder(os.path.join(app.config['DATA_FOLDER'],name))

        return redirect(url_for('auth.signin'))
    if request.method == "GET":
        if current_user.is_authenticated:
            return redirect('/portfolio')
        return render_template('auth/signup.html') 

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have successfully logged yourself out.')
    return redirect(url_for('auth.signin'))