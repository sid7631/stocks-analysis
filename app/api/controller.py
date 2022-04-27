# Import flask dependencies
from flask import Blueprint, request, render_template, flash, g, session, redirect, url_for
from flask_cors import cross_origin
import os

# Import password / encryption helper tools
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from app.api.utils import tax_stocks

# Import the database object from the main app module
from app.db_config import db

# Import module forms
from app.auth.forms import LoginForm

# Import module models (i.e. User)
from app.auth.models import User

from flask import current_app as app, send_from_directory

# Define the blueprint: 'auth', set its url prefix: app.url/auth
api = Blueprint('api', __name__, url_prefix='/api')

ALLOWED_EXTENSIONS = ['csv', 'xlsx']

def allowed_file(filename):
    extension = filename.rsplit('.', 1)[1].lower()
    print(extension)
    return filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Set the route and accepted methods
@api.route('/upload', methods=['POST','GET'])
@cross_origin()
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            print('No file part')
            return 'No file part'
        file = request.files['file']
        filename = secure_filename(file.filename)
        if filename == '':
            print('No selected file')
            return 'No selected file'

        if allowed_file(filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'],session.get("name"), filename))
            session["tax_filename"] = filename

            data = tax_stocks(os.path.join(session.get('userpath'),session.get('tax_filename')))
            # data = tax_stocks('./data/sid/2021Q1.csv')
            
            # return jsonify([{"category":"Short Term Capital Gain (STT paid)","label":"loss","pnl":189838.69},{"category":"Short Term Capital Gain (STT paid)","label":"profit","pnl":271110.5},{"category":"Speculation Income (STT paid)","label":"loss","pnl":98426.22},{"category":"Speculation Income (STT paid)","label":"profit","pnl":138592.35}])

            return data

        else:
            return 'file extension not allowed'