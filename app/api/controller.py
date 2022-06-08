# Import flask dependencies
from crypt import methods
import logging
from flask import Blueprint, jsonify, request, render_template, flash, g, session, redirect, url_for, Response
from flask_cors import cross_origin
import os
import pandas as pd
from app.api.casimoprter import import_cas
from app.api.mutual_fund import mutual_fund_summary

from app.tasks import celery

# Import password / encryption helper tools
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from app.api.models import Holdings, Portfolio
from app.api.utils import  init_mf_portfolio, tax_stocks, upload_files
import json


# Import the database object from the main app module
from app.app_config import db

# Import module forms
from app.auth.forms import LoginForm

# Import module models (i.e. User)
from app.auth.models import User

from flask import current_app as app, send_from_directory

from flask_login import LoginManager, login_user, login_required, current_user, logout_user

from app.tasks import create_task

# Define the blueprint: 'auth', set its url prefix: app.url/auth
api = Blueprint('api', __name__, url_prefix='/api')

ALLOWED_EXTENSIONS_TAX = ['csv', 'xlsx']

ALLOWED_EXTENSIONS_MF = ['pdf']

logger = logging.getLogger(__name__)

def allowed_file(filename, ALLOWED_EXTENSIONS):
    extension = filename.rsplit('.', 1)[1].lower()
    print(extension)
    return filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Set the route and accepted methods
# @api.route('/upload/tax', methods=['POST','GET'])
# @cross_origin()
# @login_required
# def upload_tax():
#     if request.method == 'POST':
#         if 'file' not in request.files:
#             print('No file part')
#             return 'No file part'
#         file = request.files['file']
#         filename = secure_filename(file.filename)
#         if filename == '':
#             print('No selected file')
#             return 'No selected file'

#         if allowed_file(filename, ALLOWED_EXTENSIONS_TAX):
#             filename = secure_filename(file.filename)
#             print(current_user, app.root_path, app.instance_path, os.path.dirname(app.instance_path))
#             file.save(os.path.join(app.config['DATA_FOLDER'],current_user.name, filename))
#             session["tax_filename"] = filename

#             data = tax_stocks(os.path.join(app.config['DATA_FOLDER'],current_user.name, filename))
#             # data = tax_stocks('./data/sid/2021Q1.csv')
            
#             # return jsonify([{"category":"Short Term Capital Gain (STT paid)","label":"loss","pnl":189838.69},{"category":"Short Term Capital Gain (STT paid)","label":"profit","pnl":271110.5},{"category":"Speculation Income (STT paid)","label":"loss","pnl":98426.22},{"category":"Speculation Income (STT paid)","label":"profit","pnl":138592.35}])

#             return data

#         else:
#             return 'file extension not allowed'

@api.route('/upload/tax', methods=['POST','GET'])
@cross_origin()
@login_required
def upload_tax():
    if request.method == 'POST':
        file_path = os.path.join(app.config['DATA_FOLDER'],current_user.name)
        file_meta = upload_files(request,file_path,allowed_extensions=ALLOWED_EXTENSIONS_TAX)
        if file_meta['status'] == 200:
            print('success')
            data = tax_stocks(os.path.join(file_path,file_meta['filename']))
            return data, 200
        else:
            return file_meta['message'], 400

@api.route('/holdings', methods=['POST', 'GET'])
@cross_origin()
def holdings():
    if request.method == 'POST':
        holdings_data = pd.read_csv(os.path.join('drive','test', 'holdings.csv'))
        holdings_object = []
        for row in holdings_data.to_records():
            holdings_object.append(Holdings(symbol=row[1],sector=row[2],quantity=row[3],price=row[4]))
        db.session.bulk_save_objects(holdings_object)
        db.session.commit()
        return 'ok'
    
@api.route('/upload/mutualfund', methods=['POST', 'GET'])
@cross_origin()
def upload_mutual_fund():
    if request.method == 'POST':
        file_path = os.path.join(app.config['DATA_FOLDER'],current_user.name)
        file_meta = upload_files(request,file_path,allowed_extensions=ALLOWED_EXTENSIONS_MF)
        if file_meta['status'] == 200:
            logger.info("logged in user %s",str(current_user.id))
            data = init_mf_portfolio(os.path.join(file_path,file_meta['filename']))
            response_obj = import_cas(data,current_user.id)
        #     #update portfolio
        #     portfolio = Portfolio.query.filter_by(email=data['investor_info']['email']).first()
        #     if portfolio:
        #         print(portfolio)
        #     else:
        #         new_portfolio = Portfolio(user=current_user.id,name=data['investor_info']['name'],email=data['investor_info']['email'])
        #         db.session.add(new_portfolio)
        #         db.session.commit()
        #     return data, 200
        # else:
        #     return file_meta['message'], 400
        return response_obj, 200

@api.route("/tasks", methods=["POST"])
def run_task():
    content = request.json
    task_type = content["type"]
    task = create_task.delay(int(task_type))
    return jsonify({"task_id": task.id}), 202

@api.route("/tasks/<task_id>", methods=["GET"])
def get_status(task_id):
    # task_result = AsyncResult(task_id)
    task_result = celery.AsyncResult(task_id)
    result = {
        "task_id": task_id,
        "task_status": task_result.status,
        "task_result": task_result.result
    }
    return jsonify(result), 200

@api.route('/mutualfund', methods=['POST', 'GET'])
@cross_origin()
def mutual_fund():
    if request.method == 'GET':
        # data = mutual_fund_summary(current_user.id)
        data = mutual_fund_summary(1)
        response_obj = jsonify(data)
        return response_obj, 200