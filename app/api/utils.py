import code
from email import message
import pandas as pd
import datetime
import json
from pathlib import Path
from sqlalchemy import null
from werkzeug.utils import secure_filename
import os
import casparser
from mftool import Mftool
from casparser.types import CASParserDataType, FolioType
from sqlalchemy.orm.exc import NoResultFound
from typing import List
import re
from rapidfuzz import process
from dateutil.parser import parse as dateparse
from sqlalchemy.dialects.sqlite import insert


from app.api.models import Portfolio

# from app.api.models import AMC, Folio, FolioScheme, FundScheme, Portfolio, SchemeValue, Transaction
# from app.tasks import fetch_nav
# mf = Mftool()

RTA_MAP = {"CAMS": "CAMS", "FTAMIL": "FRANKLIN", "KFINTECH": "KARVY", "KARVY": "KARVY"}

ALLOWED_EXTENSIONS_TAX = ['csv', 'xlsx']

ALLOWED_EXTENSIONS_MF = ['pdf']

def allowed_file(filename, ALLOWED_EXTENSIONS):
    extension = filename.rsplit('.', 1)[1].lower()
    print(extension)
    return filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def tax_stocks(file_path,start_date=None,end_date=None):
    icici_tax_statement_mapping = {
        'column_names':{'Description':'category','Stock Symbol':'symbol','Quantity':'quantity','Sale Date':'sale_date','Sale Rate':'sale_rate','Sale Value':'sale_value','Purchase Date':'purchase_date','Purchase Rate':'purchase_rate','Purchase Value':'purchase_value','Profit/Loss(-)':'pnl'}
    }
    sheet_mapping = icici_tax_statement_mapping
    df = pd.read_csv(file_path, skiprows=2)
    #interpolate first column with nearest value
    df.iloc[:,0] = df.iloc[:,0].ffill()
    #drop any column with nan
    df.drop(df.index[df.isnull().any(1)], inplace=True)
    #reset index
    df.reset_index(drop=True,inplace=True)
    #make first row column and remove the first row
    # df.columns = df.iloc[0]
    # df = df[1:]
    #rename columns based on mapping
    df.columns = df.columns.to_series().map(sheet_mapping['column_names'])

    df['sale_date'] = pd.to_datetime(df['sale_date']).dt.date
    df['purchase_date'] = pd.to_datetime(df['purchase_date']).dt.date
    df['label'] = df['pnl'].apply(lambda x: 'loss' if x.startswith('-') else 'profit')
    for column in ['sale_rate','sale_value','purchase_rate','purchase_value','pnl']:
        df[column] = df[column].apply(lambda x: x.replace('-','').replace(',',''))
        df[column] = pd.to_numeric(df[column])
    if start_date and end_date:
        x = datetime.datetime.strptime(start_date,'%d-%m-%Y').date()
        y = datetime.datetime.strptime(end_date,'%d-%m-%Y').date()
        df_date_filtered = df[(df['sale_date']>=x) & (df['sale_date']<=y)]
    else:
        df_date_filtered = df
        start_date = df['sale_date'].min()
        end_date = df['sale_date'].max()
    df_result = pd.DataFrame(df_date_filtered.groupby(['category','label'])['pnl'].sum().reset_index())
    return {'records':json.loads(df_result.to_json(orient='records')), 'from':start_date, 'to':end_date}

def upload_files(request, file_path,allowed_extensions):
    if 'file' not in request.files:
        print('No file part')
        return {"status":404,"mesage":'No file part'}
    file = request.files['file']
    filename = secure_filename(file.filename)
    if filename == '':
        print('No selected file')
        return {"status":404,"mesage":'No selected file'}
    if allowed_file(filename, allowed_extensions):
        file.save(os.path.join(file_path, filename))
        return {"status":200, "message":"Uploaded", "filename":filename}
    else:
        return {"status":404,"message":'file extension not allowed'}

def init_mf_portfolio(file_path):
    data = casparser.read_cas_pdf(file_path, "Sid@78088")
    return data

def get_or_create(session, model, **kwargs):
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        session.add(instance)
        session.commit()
        return instance

def insert_or_update(session,model,index_elements,**kwargs):
    insert_stmt = insert(model).values(**kwargs)
    do_update_stmt = insert_stmt.on_conflict_do_update(index_elements=index_elements,set_= dict(**kwargs))
    session.execute(do_update_stmt)
    session.commit()
    return session.query(model).filter_by(**kwargs).first()