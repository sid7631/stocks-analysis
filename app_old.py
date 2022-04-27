from crypt import methods
from django.shortcuts import render
from flask import Flask, render_template,send_from_directory,request, jsonify, make_response, session, redirect, url_for, flash
from flask_cors import CORS, cross_origin
import os
import time
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_session import Session
from pathlib import Path
import datetime
from flask_sqlalchemy import SQLAlchemy
from models import User, db
from flask_login import LoginManager, login_user, login_required, current_user, logout_user

from utils import tax_stocks

app = Flask(__name__ ,static_folder='client/build',static_url_path='')
app.config['SECRET_KEY'] = 'your secret key'
app.config['CORS_HEADERS'] = 'Content-Type'
app.config['UPLOAD_FOLDER'] = './data'
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
cors = CORS(app)
Session(app)

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    # since the user_id is just the primary key of our user table, use it in the query for the user
    return User.query.get(int(user_id))


ALLOWED_EXTENSIONS = ['csv', 'xlsx']


def allowed_file(filename):
    extension = filename.rsplit('.', 1)[1].lower()
    print(extension)
    return filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#Routes -------------


# @app.route('/api')
# @cross_origin()
# def Welcome():
#     return "Welcome to the API!!!"


@app.route("/")
def index():
    # if not session.get("name"):
    #     return redirect("/login")
    return render_template('index.html')
  
  
@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        # session["name"] = request.form.get("name")
        # #create user folder if doesn't exist and set path in session
        # os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'],session.get("name")), exist_ok=True)
        # session["userpath"] = os.path.join(app.config['UPLOAD_FOLDER'],session.get("name"))

        # login code goes here
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = User.query.filter_by(email=email).first()

        # check if the user actually exists
        # take the user-supplied password, hash it, and compare it to the hashed password in the database
        if not user or not check_password_hash(user.password, password):
            flash('Please check your login details and try again.')
            return redirect(url_for('login')) # if the user doesn't exist or password is wrong, reload the page

        # if the above check passes, then we know the user has the right credentials
        login_user(user, remember=remember)
        return redirect("/stocks_analysis")
    if request.method == "GET":
        if current_user.is_authenticated:
            return redirect("/stocks_analysis")
        return render_template("login.html")

@app.route("/signup", methods=["POST", "GET"])
def signup():
    if request.method == "POST":
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user: # if a user is found, we want to redirect back to signup page so user can try again
            flash('Email address already exists')
            return redirect(url_for('signup'))

        new_user = User(email=email, name=name, password=generate_password_hash(password, method='sha256'))

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))
    if request.method == "GET":
        if current_user.is_authenticated:
            return redirect("/stocks_analysis")
        return render_template('signup.html') 
  
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route("/profile", methods=["GET", "POST"])
def profile():
    if request.method == 'GET':
        return render_template("profile.html")

@app.route('/api/upload', methods=['POST','GET'])
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

@app.route('/api/tax/filter', methods=['POST','GET'])
@cross_origin()
def tax_filter():
    if request.method == 'GET':
        # print(request.args.get('from'))
        # print(request.args.get('to'))
        from_date = request.args.get('from')
        to_date = request.args.get('to')

        print(to_date,from_date)
        data = tax_stocks(os.path.join(session.get('userpath'),session.get('tax_filename')),to_date,from_date)
        # data = tax_stocks('./data/sid/2021Q1.csv',to_date,from_date)

        # print(datetime.datetime.strptime(from_date,'%d-%m-%Y').date())
        # return jsonify([{"category":"Short Term Capital Gain (STT paid)","label":"loss","pnl":8838.69},{"category":"Short Term Capital Gain (STT paid)","label":"profit","pnl":2110.5},{"category":"Speculation Income (STT paid)","label":"loss","pnl":8426.22},{"category":"Speculation Income (STT paid)","label":"profit","pnl":38592.35}])
        return data



@app.route('/stocks_analysis/', defaults={'path': ''})
@app.route('/stocks_analysis/<path:path>')
@login_required
def serve(path):
    # print(path)
    # if not session.get("name"):
    #     return redirect("/login")
    print(current_user)
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == "__main__":
   app.run(debug=True)