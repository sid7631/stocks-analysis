from crypt import methods
from flask import Flask, render_template,send_from_directory,request, jsonify, make_response, session, redirect
from flask_cors import CORS, cross_origin
import os
import time
from werkzeug.utils import secure_filename
from flask_session import Session
from pathlib import Path

from utils import tax_stocks

app = Flask(__name__ ,static_folder='client/build',static_url_path='')
app.config['SECRET_KEY'] = 'your secret key'
app.config['CORS_HEADERS'] = 'Content-Type'
app.config['UPLOAD_FOLDER'] = './data'
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
cors = CORS(app)
Session(app)


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
    if not session.get("name"):
        return redirect("/login")
    return render_template('index.html')
  
  
@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        session["name"] = request.form.get("name")
        #create user folder if doesn't exist and set path in session
        os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'],session.get("name")), exist_ok=True)
        session["userpath"] = os.path.join(app.config['UPLOAD_FOLDER'],session.get("name"))
        return redirect("/stocks_analysis")
    if request.method == "GET":
        if session.get("name"):
            return redirect("/")
        return render_template("login.html")
  
  
@app.route("/logout")
def logout():
    session["name"] = None
    return redirect("/")
  

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
            
            # return jsonify([{"Description":"Short Term Capital Gain (STT paid)","label":"loss","Profit\/Loss(-)":189838.69},{"Description":"Short Term Capital Gain (STT paid)","label":"profit","Profit\/Loss(-)":271110.5},{"Description":"Speculation Income (STT paid)","label":"loss","Profit\/Loss(-)":98426.22},{"Description":"Speculation Income (STT paid)","label":"profit","Profit\/Loss(-)":138592.35}])

            return data

        else:
            return 'file extension not allowed'


@app.route('/stocks_analysis/', defaults={'path': ''})
@app.route('/stocks_analysis/<path:path>')
def serve(path):
    print(path)
    if not session.get("name"):
        return redirect("/login")
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == "__main__":
   app.run(debug=True)