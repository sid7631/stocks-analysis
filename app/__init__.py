# Import flask and template operators
import os
from pathlib import Path
from flask import Flask, render_template
from flask_login import LoginManager

# Import SQLAlchemy


from flask_wtf.csrf import CSRFProtect
from app.api.utils import create_folder
from app.auth.models import User



from config import Config
from app.db_config import db


# Define the WSGI application object
app = Flask(__name__,static_folder='client/build',static_url_path='')

# Configurations
app.config.from_object('config.DevelopmentConfig')
# app.secret_key = 'secret'

# Define the database object which is imported
# by modules and controllers

# csrf = CSRFProtect(app)




# Sample HTTP error handling
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

# Import a module / component using its blueprint handler variable (mod_auth)
from app.auth.controllers import auth as auth
from app.portfolio.controllers import portfolio as portfolio
from app.api.controller import api as api

# Register blueprint(s)
app.register_blueprint(auth)
app.register_blueprint(portfolio)
app.register_blueprint(api)



# Build the database:
# This will create the database file using SQLAlchemy
db.init_app(app)
db.app = app
db.create_all()

create_folder(app.config['DATA_FOLDER'])



login_manager = LoginManager()
login_manager.login_view = 'auth.signin'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    # since the user_id is just the primary key of our user table, use it in the query for the user
    return User.query.get(int(user_id))

