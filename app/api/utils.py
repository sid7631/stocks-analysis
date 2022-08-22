import code
from email import message
import numpy as np
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
import logging
from app.api.models import  AMC, Folio, Portfolio, FolioScheme, FolioValue, FundScheme, NAVHistory, PortfolioValue, SchemeValue, Transaction
from app.app_config import db
from sqlalchemy.sql import func
from sqlalchemy import asc, null, select
from decimal import Decimal
from typing import Optional, Union
from collections import deque
from sqlalchemy import desc


from app.api.models import Portfolio

# from app.api.models import AMC, Folio, FolioScheme, FundScheme, Portfolio, SchemeValue, Transaction
# from app.tasks import fetch_nav
# mf = Mftool()

logger = logging.getLogger(__name__)

RTA_MAP = {"CAMS": "CAMS", "FTAMIL": "FRANKLIN", "KFINTECH": "KARVY", "KARVY": "KARVY"}

ALLOWED_EXTENSIONS_TAX = ['csv', 'xlsx']

ALLOWED_EXTENSIONS_MF = ['pdf']

class TransactionLike:
    amount: Union[Decimal, float, None]
    nav: Union[Decimal, float, None]
    units: Union[Decimal, float, None]
    type: str

class FIFOUnits:
    def __init__(
        self, balance=Decimal("0.000"), invested=Decimal("0.00"), average=Decimal("0.0000")
    ):
        self.transactions = deque()
        self.balance = balance
        self.invested = invested
        self.average = average
        self.pnl = Decimal("0.00")

    def __str__(self):
        return f"""
Number of transactions : {len(self.transactions)}
Balance                : {self.balance}
Invested               : {self.invested}
Average NAV            : {self.average}
PNL                    : {self.pnl}"""

    def add_transaction(self, txn: TransactionLike):
        """Add transaction to the FIFO Queue.
        Note: The Transactions should be sorted date-wise (preferably using the
        `sort_transactions=True` option via casparser
        """
        quantity = Decimal(str(txn.units or "0.000"))
        nav = Decimal(str(txn.nav or "0.0000"))
        if txn.amount is None:
            return
        elif txn.amount > 0 and txn.sub_type != "STT_TAX":
            self.buy(quantity, nav, amount=txn.amount)
        elif txn.amount < 0:
            self.sell(quantity, nav)

    def sell(self, quantity: Decimal, nav: Decimal):
        original_quantity = abs(quantity)
        pending_units = original_quantity
        cost_price = Decimal("0.000")
        price = None
        while pending_units > 0:
            try:
                units, price = self.transactions.popleft()
                if units <= pending_units:
                    cost_price += units * price
                else:
                    cost_price += pending_units * price
                pending_units -= units
            except IndexError:
                break
        if pending_units < 0 and price is not None:
            # Re-add the remaining units to the FIFO queue
            self.transactions.appendleft((-1 * pending_units, price))
        self.invested -= Decimal(round(cost_price, 2))
        self.balance -= original_quantity
        self.pnl += Decimal(round(original_quantity * nav - cost_price, 2))
        if abs(self.balance) > 0.01:
            self.average = Decimal(round(self.invested / self.balance, 4))
        else:
            self.average = 0

    def buy(self, quantity: Decimal, nav: Decimal, amount: Optional[Decimal] = None):
        self.balance += quantity
        if amount is not None:
            self.invested += Decimal(amount)
        if abs(self.balance) > 0.01:
            self.average = Decimal(round(self.invested / self.balance, 4))
        self.transactions.append((quantity, nav))

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


def update_portfolio_value(start_date = None, portfolio_id=None,scheme_dates=None):
    if not isinstance(scheme_dates, dict):
        scheme_dates = {}
    today = datetime.date.today()

    from_date1 = today
    if len(scheme_dates) > 0:
        from_date1 = min(scheme_dates.values())
        if isinstance(from_date1, str):
            from_date1 = dateparse(from_date1).date()
    
    from_date2 = today
    if isinstance(start_date, str) and start_date != "auto":
        from_date2 = dateparse(start_date).date()
    elif isinstance(start_date, datetime.date):
        from_date2 = start_date
    else:
        query = SchemeValue.query
        if portfolio_id is not None:
            query = query.filter(SchemeValue.scheme==FolioScheme.id,FolioScheme.folio==Folio.number, Folio.portfolio_id==portfolio_id)
        obj = query.order_by(desc("date")).first()
        if obj is not None:
            from_date2 = obj.date
    
    start_date = min(from_date1, from_date2)

    qs = FolioScheme.query.with_entities(FolioScheme.id,FolioScheme.scheme, FolioScheme.folio)
    if portfolio_id is not None:
        qs = qs.filter(FolioScheme.folio==Folio.number, Folio.portfolio_id==portfolio_id)

    # from_date_min = today
    schemes = qs.all()
    dfs=[]
    from_date_min = today
    for scheme_id,fund_scheme_id, folio_number in schemes:
        scheme = FolioScheme.query.get(scheme_id)

        frm_date = scheme_dates.get(scheme_id, start_date)
        if isinstance(frm_date, str):
            frm_date = dateparse(frm_date).date()
        
        scheme_val: SchemeValue = (
            SchemeValue.query.filter(SchemeValue.scheme==scheme_id, SchemeValue.date < frm_date).order_by(desc("date")).first()
        )

        old_txns = (
            Transaction.query.filter(Transaction.scheme==scheme_id, Transaction.date < frm_date).order_by(asc("date"))
        )

        new_txns = (
            Transaction.query.filter(Transaction.scheme==scheme_id, Transaction.date >= frm_date).order_by(asc("date"))
        )

        from_date = None
        if scheme_val is not None:
            from_date = scheme_val.date
        if new_txns.count() > 0:
            from_date = min(from_date or new_txns[0].date, new_txns[0].date)
        elif scheme_val is None or scheme_val.balance <= 1e-3:
            logger.info("Ignoring scheme :: %s", scheme)

        columns = ["invested", "avg_nav", "balance", "nav", "value"]

        dates = []
        invested = []
        average = []
        balance = []

        fifo = FIFOUnits()
        for txn in old_txns:
            fifo.add_transaction(txn)
        for txn in new_txns:
            fifo.add_transaction(txn)
            dates.append(txn.date)
            invested.append(fifo.invested)
            average.append(fifo.average)
            balance.append(fifo.balance)
        
        if fifo.balance > 1e-3:
            latest_nav = (
                NAVHistory.query.filter(NAVHistory.scheme==fund_scheme_id).order_by(desc("date")).first()
            )
            to_date = latest_nav.date if latest_nav is not None else (today - datetime.timedelta(days=1))
        elif len(dates) > 0:
            to_date = dates[-1]
        else:
            logger.info("Skipping scheme :: %s", scheme)
            continue

        scheme_transactions = pd.DataFrame(
            data={"invested": invested, "avg_nav":average, "balance": balance}, index=dates
        )

        from_date_min = min(from_date, from_date_min)

        index = pd.date_range(from_date, to_date)
        scheme_vals = pd.DataFrame(
            data=[[np.nan] * len(columns)] * len(index), index=index, columns=columns
        )
        if to_date !=today:
            SchemeValue.query.filter(SchemeValue.scheme==scheme_id, SchemeValue.date > to_date).delete()
            # FolioValue.query.filter(FolioValue.folio==FolioScheme.folio, FolioScheme.id==scheme_id, FolioValue.date > to_date).delete(synchronize_session='fetch')
            FolioValue.query.filter(FolioValue.folio == select([FolioScheme.folio]).where(FolioScheme.id == scheme_id).scalar_subquery(), FolioValue.date >= from_date_min).delete(synchronize_session='fetch')
            PortfolioValue.query.filter(PortfolioValue.portfolio_id== select([Folio.portfolio_id]).where(Folio.number == folio_number).scalar_subquery(), PortfolioValue.date > to_date).delete(synchronize_session='fetch')
            # PortfolioValue.query.filter(PortfolioValue.portfolio_id==Folio.portfolio_id,Folio.number==FolioScheme.folio, FolioScheme.id==scheme_id, PortfolioValue.date > to_date).delete(synchronize_session='fetch')
        if scheme_val is not None:
            scheme_vals.iloc[0] = [
                scheme_val.invested,
                scheme_val.avg_nav,
                scheme_val.balance,
                scheme_val.nav,
                scheme_val.value,
            ]
        scheme_vals.loc[
            scheme_transactions.index, ["invested", "avg_nav", "balance"]
        ] = scheme_transactions[["invested", "avg_nav", "balance"]]

        qs = (
            NAVHistory.query.with_entities(NAVHistory.date, NAVHistory.nav).filter(NAVHistory.scheme==fund_scheme_id, NAVHistory.date >= from_date, NAVHistory.date <= to_date).all()
        )
        nav_df = pd.DataFrame(data=qs, columns=["date", "nav"])
        nav_df["date"] = pd.to_datetime(nav_df["date"])
        nav_df.set_index("date", inplace=True)
        scheme_vals.loc[nav_df.index, ["nav"]] = nav_df
        scheme_vals.ffill(inplace=True)
        scheme_vals.fillna(value=0, inplace=True)
        scheme_vals["value"] = scheme_vals["nav"] * scheme_vals["balance"]
        scheme_vals["scheme"] = str(scheme_id)
        scheme_vals = scheme_vals.reset_index().rename(columns={"index": "date"})
        dfs.append(scheme_vals)
    if len(dfs) == 0:
        logger.info("No data found. Exiting..")
        return
    final_df = pd.concat(dfs)
    final_df['date'] = final_df['date'].dt.date
    logger.info(f"SchemeValue :: {len(final_df)} rows")
    for row in final_df.to_records():
        updated_scheme_value = insert_or_update(db.session, SchemeValue,['scheme','date'] ,date=row[1], invested=row[2], avg_nav=row[3], balance=row[4], nav=row[5], value=row[6], scheme=row[7])
    logger.info("SchemeValue Imported")

    logger.info("Updating FolioValue")

    columns = ["invested", "value", "avg_nav", "nav", "balance", "scheme","folio"]
    svs = db.session.query(SchemeValue,FolioScheme).with_entities(SchemeValue.date, SchemeValue.invested, SchemeValue.value, SchemeValue.avg_nav, SchemeValue.nav,SchemeValue.balance,SchemeValue.scheme,FolioScheme.folio).filter(SchemeValue.scheme==FolioScheme.id,SchemeValue.date >= from_date_min)
    if portfolio_id is not None:
        svs = svs.filter(FolioScheme.folio==Folio.number, Folio.portfolio_id==portfolio_id)
    svs = svs.order_by(asc("scheme"),asc("date"))
    sval_df = pd.DataFrame(data=svs.all(), columns=["date"]+columns)
    sval_df.set_index("date", inplace=True)
    dfs = []
    for scheme, group in sval_df.groupby("scheme"):
        rows, _ = group.shape
        if rows == 0:
            continue
        from_date = group.index.values[0]
        balance = group.iloc[-1].balance
        if balance > 0:
            to_date = today
        else:
            to_date = group.index.values[-1]
        index = pd.date_range(from_date, to_date)
        df = pd.DataFrame(data=[[np.nan] * len(columns)] * len(index), index=index, columns=columns)
        df.loc[group.index, columns] = group.loc[group.index, columns]
        df.ffill(inplace=True)
        dfs.append(df)

    if len(dfs) > 0:
        merged_df = pd.concat(dfs)
        merged_df["scheme"] = merged_df["scheme"].astype("int")
        merged_df["folio"] = merged_df["folio"].astype("int")

        merged_df = merged_df.reset_index().rename(
            columns={"index": "date", "folio": "folio"}
        )
        merged_df = (
            merged_df.groupby(["date", "folio"])[["invested", "value"]].sum().reset_index()
        )
        merged_df['date'] = merged_df['date'].dt.date
        merged_df['folio'] = merged_df["folio"].astype("string")
        for row in merged_df.to_records():
            updated_folio_value = insert_or_update(db.session, FolioValue,['folio','date'] ,date=row[1], folio=row[2], invested=row[3], value=row[4])
    logger.info("FolioValue updated")

    logger.info("Updating PortfolioValue")
    
    query = db.session.query(FolioValue,Folio).with_entities(FolioValue.date,func.sum(FolioValue.invested), func.sum(FolioValue.value),Folio.portfolio_id).filter(FolioValue.folio==Folio.number, FolioValue.date >= from_date_min)
    if portfolio_id is not None:
        query = query.filter(Folio.portfolio_id==portfolio_id)
    query = query.group_by(FolioValue.date, Folio.portfolio_id)

    for row in query.all():
        portfolio_value_update = insert_or_update(db.session,PortfolioValue,['portfolio_id','date'], date=row[0],invested=row[1],value=row[2],portfolio_id=portfolio_id)
    logger.info('PortfolioValue updated')


    print('ok')
















