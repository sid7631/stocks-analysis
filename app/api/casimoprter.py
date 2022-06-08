import code
from email import message
import pandas as pd
import datetime
import json
from pathlib import Path
import pytz
import requests
from sqlalchemy import asc, null, select
from werkzeug.utils import secure_filename
import os
import casparser
from casparser.types import CASParserDataType, FolioType, SchemeType, TransactionDataType
from sqlalchemy.orm.exc import NoResultFound
from typing import List
import re
from rapidfuzz import process
from dateutil.parser import parse as dateparse
from sqlalchemy.dialects.sqlite import insert
import logging
from dateutil.parser import parse as date_parse
import time
from sqlalchemy import desc
from decimal import Decimal
from typing import Optional, Union
from collections import deque
from app.api.models import  AMC, Folio, FolioScheme, FolioValue, FundScheme, NAVHistory, Portfolio, PortfolioValue, SchemeValue, Transaction
from app.api.utils import get_or_create, insert_or_update
import numpy as np
from sqlalchemy.sql import func
from app.app_config import db

logger = logging.getLogger(__name__)



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

def import_cas(data: CASParserDataType, user_id):

    #investor info
    investor_info = data.get("investor_info", {}) or {}
    period = data['statement_period']
    logger.info('statement from %s to %s found',period["from"], period["to"])


    #prepare for portfolio update
    email = (investor_info.get("email") or "").strip()
    name = (investor_info.get("name") or "").strip()
    pan = (investor_info.get("pan") or "").strip()

    if not (email and name):
        raise ValueError("Email or Name invalid!")
    
    portfolio = insert_or_update(db.session,Portfolio,['pan','email'],email=email, name=name, user=user_id, pan=pan)
    logger.info('portfolio %s for %s',str(portfolio.id),portfolio.name)


    folios: List[FolioType] = data.get("folios", []) or []
    folios_list = set()
    schemes_list = set()
    fund_schemes_list = set()
    scheme_dates = {}

    for row in folios:
        amc = (row.get("amc") or "").strip()
        pan = (row.get("PAN") or "").strip()
        kyc = (row.get("KYC") or "").strip()
        pankyc = (row.get("PANKYC") or "").strip()
        number = (row.get("folio") or "").split('/')[0].strip()
        schemes: List[SchemeType] = row.get("schemes",[]) or []

        amc = get_or_create(db.session,AMC,name=amc)
        folio = get_or_create(db.session, Folio, amc = amc.name, portfolio_id=portfolio.id,number=number,pan=pan,kyc=Folio.get_pan_kyc(kyc),pan_kyc=Folio.get_pan_kyc(pankyc))
        logger.info('amc %s and folio %s',str(amc.name), str(folio.number))

        for scheme_row in schemes:
            name = (scheme_row.get("scheme") or "").strip()
            rta = (scheme_row.get("rta") or "").strip()
            category = (scheme_row.get("type") or "").strip()
            plan = FundScheme.get_fund_plan(name)
            rta_code = (scheme_row.get("rta_code") or "").strip()
            amfi_code = (scheme_row.get("amfi") or "").strip()
            isin = (scheme_row.get("isin") or "").strip()
            valuation = scheme_row.get("valuation", {}) or {}

            fund_scheme = get_or_create(db.session, FundScheme, name=name,amc=amc.name,rta=rta,category=category,plan=plan,rta_code=rta_code,amfi_code=amfi_code, isin=isin)
            folio_scheme = insert_or_update(db.session, FolioScheme, ['scheme','folio'], scheme=fund_scheme.id, folio=folio.number, valuation=valuation["value"],valuation_date = valuation["date"])
            logger.info('fund_scheme %s and folio_scheme %s',str(fund_scheme.name), str(folio_scheme.folio))

            transactions:List[TransactionDataType] = scheme_row.get("transactions",[]) or []
            balance = 0

            latest_transaction = Transaction.query.filter(Transaction.scheme==folio_scheme.id).order_by(desc("date")).first()
            
            if latest_transaction is None:
                latest_transaction_date = datetime.date(1970,1,1)
            else:
                latest_transaction_date = latest_transaction.date
            
            min_date = None
            for txn in transactions:
                if txn["balance"] is None:
                    txn["balance"] = balance
                else:
                    balance = txn["balance"]
                    txn_date = txn["date"]
                    if txn_date <= latest_transaction_date:
                        continue
                    transaction = get_or_create(db.session, Transaction, scheme=folio_scheme.id, date=txn_date, balance=balance, units=txn["units"],description=txn["description"], amount=txn["amount"], nav=txn["nav"], order_type=Transaction.get_order_type(txn["description"], txn["amount"]), sub_type=txn["type"])
                    min_date = min(txn_date, min_date or txn_date)
            
            if min_date is not None:
                scheme_dates[folio_scheme.id]=min_date

            if fund_scheme.id not in fund_schemes_list:
                fund_schemes_list.add(fund_scheme.id)

    fetch_nav(
            fund_schemes_list,
            update_portfolio_kwargs={
                "from_date": "auto",
                "portfolio_id": portfolio.id,
                "scheme_dates": scheme_dates,
            }
        )
    


    return 'ok'


def fetch_nav(fund_schemes_list=None,update_portfolio_kwargs=None):
    today = datetime.date.today()
    qs = FundScheme.query
    if isinstance(fund_schemes_list, list):
        qs = qs.filter(FundScheme.id.in_(list(fund_schemes_list)))
    for fund_scheme in qs.all():
        code = fund_scheme.amfi_code

        if code is None:
            logger.info('"Unable to lookup code for %s" % code')
            continue

        latest_nav_ = NAVHistory.query.filter_by(scheme=fund_scheme.id).order_by(desc("date")).first()

        if latest_nav_ is not None:
            latest_nav_date = latest_nav_.date
        else:
            latest_nav_date = datetime.date(1970,1,1)
        
        if latest_nav_date == today:
            logger.info("Nav for %s is updated, skipping",code)
            continue

        logger.info("Fetching NAV for %s from %s", code, latest_nav_date.isoformat())

        mfapi_url = f"https://api.mfapi.in/mf/{code}"
        response = requests.get(mfapi_url, timeout=60)
        data = response.json()
        for item in reversed(data["data"]):
            date = date_parse(item["date"], dayfirst=True).date()
            if date <= latest_nav_date:
                continue
            
            nav_history = get_or_create(db.session, NAVHistory, scheme=fund_scheme.id, date=date, nav=item["nav"])
        
        time.sleep(2)
    logger.info("Finished adding Nav History")

    kwargs = {}
    if isinstance(update_portfolio_kwargs, dict):
        kwargs.update(update_portfolio_kwargs)
    else:
        kwargs.update(from_date='auto')
    
    update_portfolios(**kwargs)



def update_portfolios(from_date = None, portfolio_id=None, scheme_dates=None):
    update_portfolio_value(start_date = from_date, portfolio_id=portfolio_id,scheme_dates=scheme_dates)

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
    query = query.group_by(FolioValue.date)

    for row in query.all():
        portfolio_value_update = insert_or_update(db.session,PortfolioValue,['portfolio_id','date'], date=row[0],invested=row[1],value=row[2],portfolio_id=portfolio_id)
    logger.info('PortfolioValue updated')


    print('ok')











































    