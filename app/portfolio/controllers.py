# Import flask dependencies
from flask import Blueprint, request, render_template, flash, g, session, redirect, url_for

# Import password / encryption helper tools
from werkzeug.security import check_password_hash, generate_password_hash

# Import the database object from the main app module
from app.app_config import db

# Import module forms
from app.auth.forms import LoginForm

# Import module models (i.e. User)
from app.auth.models import User

from flask import current_app as app, send_from_directory

from flask_login import LoginManager, login_user, login_required, current_user, logout_user

# Define the blueprint: 'auth', set its url prefix: app.url/auth
portfolio = Blueprint('portfolio', __name__, url_prefix='/portfolio/')

# Set the route and accepted methods
@portfolio.route('/', defaults={'path': ''})
@portfolio.route('/<path:path>')
@login_required
def portfolio_base(path):
    print(app.static_folder)
    # return 'ok'
    return send_from_directory(app.static_folder, 'index.html')