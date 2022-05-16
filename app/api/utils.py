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

from app.api.models import AMC, Folio, FolioScheme, FundScheme, Portfolio, SchemeValue, Transaction
from app.tasks import fetch_nav
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

def db_master_init(db):
    amc_object = []
    mf_data = mf.get_scheme_codes()
    for code, name in mf_data.items():
        amc_object.append(AMC(name=name,code=code))
    if len(amc_object):
        db.session.query(AMC).delete()
        # db.session.commit()
    db.session.bulk_save_objects(amc_object)
    db.session.commit()


def import_cas(data: CASParserDataType, user_id,db):
    investor_info = data.get("investor_info", {}) or {}
    period = data["statement_period"]

    email = (investor_info.get("email") or "").strip()
    name = (investor_info.get("name") or "").strip()
    if not (email and name):
        raise ValueError("Email or Name invalid!")

    # try:
    pf = Portfolio.query.filter_by(email=data['investor_info']['email']).first()
    if pf == None:
        pf = Portfolio(email=email, name=name, user=user_id, pan=(investor_info.get("pan") or "").strip())
        db.session.add(pf)
    


    num_created = 0
    num_total = 0
    new_folios = 0

    folios: List[FolioType] = data.get("folios", []) or []
    fund_scheme_ids = []
    scheme_dates = {}
    for folio in folios:
        #insert amc
        amc = AMC.query.filter_by(name=folio['amc']).first()
        new_folio = Folio.query.filter_by(number=folio['folio']).first()

        for scheme in folio["schemes"]:
            if amc == None:
                #add amc to db
                amc = AMC(code=scheme['amfi'],name=folio['amc'])
                db.session.add(amc)

            folio_details = {
                'amc':amc.code,
                'portfolio':pf.id,
                'number':folio['folio'],
                'pan':folio['PAN'],
                'kyc':True if folio['KYC'] == 'OK' else False,
                'pan_kyc':True if folio['PANKYC'] == 'OK' else False
            }
            
            if new_folio == None:
                new_folio = Folio(amc=folio_details['amc'],portfolio=folio_details['portfolio'],
                    number=folio_details['number'],pan=folio_details['pan'],kyc=folio_details['kyc'],
                    pan_kyc=folio_details['pan_kyc'])
                db.session.add(new_folio)
                new_folios +=1
            

            #insert fundscheme
            scheme_details = {
                'name':scheme['scheme'],
                'amc':amc.code,
                'rta':scheme['rta'],
                'category':scheme['type'],
                'plan':FundScheme.get_fund_plan(scheme['scheme']),
                'rta_code':scheme['rta_code'],
                'amfi_code':scheme['amfi'],
                'isin':scheme['isin']
            }
            fund_scheme = FundScheme.query.filter_by(name=scheme_details['name'],amc=scheme_details['amc'],plan=scheme_details['plan'],amfi_code=scheme_details['amfi_code']).first()
            
            if fund_scheme == None:
                fund_scheme = FundScheme(name=scheme_details['name'],amc=scheme_details['amc'],rta=scheme_details['rta'],category=scheme_details['category'],
                    plan=scheme_details['plan'],rta_code=scheme_details['rta_code'],
                    amfi_code=scheme_details['amfi_code'],isin=scheme_details['isin']
                    )
                db.session.add(fund_scheme)

            folio_scheme = FolioScheme.query.filter_by(folio=new_folio.number,scheme=fund_scheme.amfi_code).first()

            if folio_scheme == None:
                valuation = scheme['valuation']
                folio_scheme = FolioScheme(scheme=fund_scheme.amfi_code,folio=new_folio.number,valuation=valuation['value'],valuation_date=valuation['date'])
                db.session.add(folio_scheme)
                folio_scheme = FolioScheme.query.filter_by(scheme=fund_scheme.amfi_code,folio=new_folio.number,valuation=valuation['value'],valuation_date=valuation['date']).first()
            fund_scheme_ids.append(folio_scheme.id)
            

            if len(scheme['transactions']) > 0:
                from_date = scheme['transactions'][0]['date']
                scheve_value = SchemeValue.query.filter_by(scheme_id=folio_scheme.id,date=from_date).first()
                if scheve_value == None:
                    scheve_value = SchemeValue(date=from_date,scheme_id=folio_scheme.id, scheme=folio_scheme.scheme,
                        nav=0,balance=scheme['open'],invested=0,value=0)
                    db.session.add(scheve_value)

            balance = 0
            min_date = None

            for transaction in scheme['transactions']:
                if transaction['balance'] is None:
                    transaction['balance'] = balance
                else:
                    balance = transaction['balance']
                    txn_date = transaction['date']

                    transaction_details = {
                        'scheme':folio_scheme.scheme,
                        'date':txn_date,
                        'balance':transaction["balance"],
                        'units':transaction['units'],
                        'description':transaction['description'].strip(),
                        'amount':transaction['amount'],
                        'nav':transaction['nav'],
                        'order_type':Transaction.get_order_type(transaction['description'],transaction['amount']),
                        'sub_type':transaction['type']
                    }

                    transaction_row = Transaction.query.filter_by(
                        scheme=transaction_details['scheme'],
                        date=transaction_details['date'],
                        balance=transaction_details['balance'],
                        units=transaction_details['units'],
                        description=transaction_details['description'],
                        amount=transaction_details['amount'],
                        nav=transaction_details['nav'],
                        order_type=transaction_details['order_type'],
                        sub_type = transaction_details['sub_type']
                    ).first()
                    
                    if transaction_row == None:
                        transaction_row= Transaction(
                            scheme=transaction_details['scheme'],
                            date=transaction_details['date'],
                            balance=transaction_details['balance'],
                            units=transaction_details['units'],
                            description=transaction_details['description'],
                            amount=transaction_details['amount'],
                            nav=transaction_details['nav'],
                            order_type=transaction_details['order_type'],
                            sub_type = transaction_details['sub_type']
                        )
                        db.session.add(transaction_row)

                        min_date = min(txn_date, min_date or txn_date)
                        num_created += 1
                    num_total += 1

            if min_date is not None:
                scheme_dates[folio_scheme.scheme] = min_date 

            db.session.commit()

            #update portfolio code here

    # fetch_nav.delay(
    #     scheme_ids=fund_scheme_ids,
    #     update_portfolio_kwargs={
    #         "from_date": "auto",
    #         "portfolio_id": pf.id,
    #         "scheme_dates": scheme_dates,
    #     },
    # )
    fetch_nav(
        scheme_ids=fund_scheme_ids,
        update_portfolio_kwargs={
            "from_date": "auto",
            "portfolio_id": pf.id,
            "scheme_dates": scheme_dates,
        },
    )

    return {
        "num_folios": new_folios,
        "transactions": {
            "total": num_total,
            "added": num_created,
        },
    }

    # return {
    #     "num_folios": new_folios,
    #     "transactions": {
    #         "total": num_total,
    #         "added": num_created,
    #     },
    # }


# def scheme_lookup(rta, scheme_name, rta_code=None, amc_code=None):
#     if rta_code is None and amc_code is None:
#         raise ValueError("Either of rta_code or amc_code should be provided.")
#     if rta_code is not None:
#         rta_code = re.sub(r"\s+", "", rta_code)

#     include = {"rta": RTA_MAP[rta.upper()]}
#     exclude = {}

#     if rta_code is not None:
#         include["rta_code"] = rta_code
#     else:
#         include["amc_code"] = amc_code

#     if "reinvest" in scheme_name.lower():
#         include["name__icontains"] = "reinvest"
#     else:
#         exclude["name__icontains"] = "reinvest"

#     qs = FundScheme.query.filter_by(**include).filter(exclude(**exclude))
#     if qs.count() == 0 and "rta_code" in include:
#         include["rta_code"] = rta_code[:-1]
#         qs = FundScheme.objects.filter(**include).exclude(**exclude)
#     return qs.all()


# def get_closest_scheme(rta, scheme_name, rta_code=None, amc_code=None):
#     qs = scheme_lookup(rta, scheme_name, rta_code=rta_code, amc_code=amc_code)
#     if qs.count() == 0:
#         raise ValueError("No schemes found")
#     schemes = dict(qs.values_list("name", "pk"))
#     key, *_ = process.extractOne(scheme_name, schemes.keys())
#     scheme_id = schemes[key]
#     return scheme_id
