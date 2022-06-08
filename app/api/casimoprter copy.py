import code
from email import message
import pandas as pd
import datetime
import json
from pathlib import Path
import requests
from sqlalchemy import asc, null, select
from werkzeug.utils import secure_filename
import os
import casparser
from casparser.types import CASParserDataType, FolioType
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
from app.api.utils import get_or_create
import numpy as np
from sqlalchemy.sql import func

logger = logging.getLogger(__name__)

def import_cas(data: CASParserDataType, user_id,db):
    investor_info = data.get("investor_info", {}) or {}
    period = data["statement_period"]

    #get investor profile
    email = (investor_info.get("email") or "").strip()
    name = (investor_info.get("name") or "").strip()
    pan = (investor_info.get("pan") or "").strip()
    
    if not (email and name):
        raise ValueError("Email or Name invalid!")

    #insert of update portfolio
    insert_stmt = insert(Portfolio).values(email=email, name=name, user=user_id, pan=pan)
    do_update_stmt = insert_stmt.on_conflict_do_update(index_elements=['pan','email'],set_=dict(email=email, name=name, user=user_id, pan=(investor_info.get("pan") or "").strip()))
    db.session.execute(do_update_stmt)
    db.session.commit()
    logger.info('inserted or updated portfolio successfully')

    #get updated portfolio id
    portfolio = Portfolio.query.filter_by(email=email,pan=pan).first()
    logger.info('retrieved portfolio %s',str(portfolio.id))

    folios: List[FolioType] = data.get("folios", []) or []

    folios_list = []
    scheme_list = []
    for folio in folios:
        #add amc if not present already
        current_amc = get_or_create(db.session,AMC,name=folio["amc"])
        logger.info('inserted or retrieved amc %s', str(current_amc.name))

        current_folio = get_or_create(db.session, Folio, amc = current_amc.name, portfolio_id=portfolio.id,number=folio["folio"].split('/')[0].strip(),pan=folio["PAN"],kyc=Folio.get_pan_kyc(folio["KYC"]),pan_kyc=Folio.get_pan_kyc(folio["PANKYC"]))
        logger.info('inserted or retrieved folio %s', str(current_folio.number))

        for scheme in folio["schemes"]:

            current_fund_scheme = get_or_create(db.session, FundScheme, name=scheme["scheme"],amc=current_amc.name,rta=scheme["rta"],category=scheme["type"],plan=FundScheme.get_fund_plan(scheme["scheme"]),rta_code=scheme["rta_code"],amfi_code=scheme["amfi"], isin=scheme["isin"])
            logger.info('inserted or retrieved fund scheme %s', str(current_fund_scheme.name))
            
            current_folio_scheme = get_or_create(db.session, FolioScheme, scheme=current_fund_scheme.id, folio=current_folio.number, valuation=scheme["valuation"]["value"],valuation_date = scheme["valuation"]["date"])
            logger.info('inserted or retrieved folio scheme %s', str(current_folio_scheme.folio))

            balance = 0
            for transaction in scheme["transactions"]:
                if transaction["balance"] is None:
                    transaction["balance"] = balance
                else:
                    balance = transaction["balance"]
                    txn_date = transaction["date"]
                    current_transaction = get_or_create(db.session, Transaction, scheme=current_folio_scheme.id, date=txn_date,balance=balance,units=transaction["units"],description=transaction["description"],amount=transaction["amount"], nav=transaction["nav"],order_type=Transaction.get_order_type(transaction["description"],transaction["amount"]),sub_type=transaction["type"] )
                    logger.info('inserted or retrieved transaction %s', str(current_transaction.description))
        
        folios_list.append(current_folio.number)
        scheme_list.append(current_folio_scheme.id)
    update_nav(db, scheme_list)
    update_scheme_value(db,scheme_list,portfolio.id)
    return 'ok'

def update_scheme_value(db, scheme_list, portfolio_id):
    today = datetime.date.today()
    from_date_min = today
    dfs = []
    for id in scheme_list:
        scheme_value: SchemeValue = SchemeValue.query.filter_by(scheme=id).order_by(desc("date")).first()
        if scheme_value is not None:
            from_date = scheme_value.date
        else:
            from_date = datetime.date(1970,1,1)
        
        old_txns = Transaction.query.filter(Transaction.scheme==id, Transaction.date < from_date).order_by(asc("date")).all()
        new_txns = Transaction.query.filter(Transaction.scheme==id, Transaction.date >= from_date).order_by(asc("date")).all()


        if len(new_txns) > 0:
            from_date = new_txns[0].date
        else:
            logger.info("Ignoring scheme with id :: %s", id)

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
            latest_nav = NAVHistory.query.filter_by(scheme=id).order_by(desc("date")).first()
            to_date = latest_nav.date if latest_nav is not None else (today - datetime.timedelta(days=1))
        elif len(dates) > 0:
            to_date = dates[-1]
        else:
            print("Skipping scheme :: %s", id)
            continue

        scheme_transactions = pd.DataFrame(
            data={"invested": invested, "avg_nav": average, "balance": balance}, index=dates
        )

        from_date_min = min(from_date, from_date_min)

        index = pd.date_range(from_date, to_date)

        scheme_values = pd.DataFrame(
            data=[[np.nan] * len(columns)] * len(index), index=index, columns=columns
        )

        if to_date !=today:
            SchemeValue.query.filter(SchemeValue.scheme==id, SchemeValue.date >= from_date_min).delete(synchronize_session='fetch')
            FolioValue.query.filter(FolioValue.folio == select([FolioScheme.folio]).where(FolioScheme.id == id).scalar_subquery(), FolioValue.date >= from_date_min).delete(synchronize_session='fetch')
            PortfolioValue.query.filter(PortfolioValue.portfolio_id == portfolio_id, PortfolioValue.date >= from_date_min).delete(synchronize_session='fetch')
        
        if scheme_value is not None:
            scheme_values.iloc[0] = [
                scheme_value.invested,
                scheme_value.avg_nav,
                scheme_value.balance,
                scheme_value.nav,
                scheme_value.value,
            ]
        scheme_values.loc[
            scheme_transactions.index, ["invested", "avg_nav", "balance"]
        ] = scheme_transactions[["invested", "avg_nav", "balance"]]

        qs = NAVHistory.query.with_entities(NAVHistory.date, NAVHistory.nav).filter(NAVHistory.scheme==id, NAVHistory.date >= from_date,  NAVHistory.date <=to_date).all()
        nav_df = pd.DataFrame(data=qs, columns=["date", "nav"])
        nav_df.set_index("date", inplace=True)
        scheme_values.loc[nav_df.index, ["nav"]] = nav_df
        scheme_values.ffill(inplace=True)
        scheme_values.fillna(value=0, inplace=True)
        scheme_values["value"] = scheme_values["nav"] * scheme_values["balance"]
        scheme_values["scheme"] = id
        scheme_values = scheme_values.reset_index().rename(columns={"index": "date"})
        dfs.append(scheme_values)
    
    if len(dfs) == 0:
        logger.info("No data found. exiting..")
        return
    final_df = pd.concat(dfs)
    logger.info(f"SchemeValue :: {len(final_df)} rows")
    for row in final_df.to_records():
        updated_scheme_value = get_or_create(db.session, SchemeValue, date=datetime.datetime.strptime(str(row[1])[:10],"%Y-%m-%d"),invested=row[2],avg_nav=row[3],balance=row[4],nav=row[5],value=row[6],scheme=int(row[7]))

    columns = ["invested", "value", "avg_nav", "nav", "balance", "scheme","folio_number"]

    svs = db.session.query(SchemeValue, FolioScheme, Folio).with_entities(SchemeValue.date,SchemeValue.invested, SchemeValue.value, SchemeValue.avg_nav, SchemeValue.nav, SchemeValue.balance, SchemeValue.scheme,FolioScheme.folio).filter(SchemeValue.date >= from_date_min)
    
    if portfolio_id is not None:
        svs = svs.filter(SchemeValue.scheme==FolioScheme.id).filter(FolioScheme.folio==Folio.number).filter(Folio.portfolio_id==portfolio_id)

    sval_df = pd.DataFrame(data=svs.all(), columns=["date"] + columns)
    sval_df.set_index("date",inplace=True)

    dfs=[]

    for scheme, group in sval_df.groupby('scheme'):
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

        # aa = group.loc[group.index, columns]
        df.loc[group.index, columns] =  group
        df.ffill(inplace=True)
        dfs.append(df)
    
    if len(dfs) > 0:
        merged_df = pd.concat(dfs)
        merged_df["scheme"] = merged_df["scheme"].astype("int")
        # merged_df["folio_number"] = merged_df["folio_number"].astype("int")

        merged_df = merged_df.reset_index().rename(
            columns={"index": "date", "folio_number": "folio"}
        )
        merged_df = (
            merged_df.groupby(["date", "folio"])[["invested", "value"]].sum().reset_index()
        )

        # for row in merged_df.to_records():
        #     insert_stmt = insert(FolioValue).values(date=datetime.datetime.strptime(str(row[1])[:10],"%Y-%m-%d"),folio=row[2],invested=row[3],value=row[4])
        #     do_update_stmt = insert_stmt.on_conflict_do_update(index_elements=['folio','date'],set_=dict(date=datetime.datetime.strptime(str(row[1])[:10],"%Y-%m-%d"),folio=row[2],invested=row[3],value=row[4]))
        #     db.session.execute(do_update_stmt)
        # db.session.commit()
        for row in merged_df.to_records():
            updated_folio_value = get_or_create(db.session,FolioValue,date=datetime.datetime.strptime(str(row[1])[:10],"%Y-%m-%d"),folio=row[2],invested=row[3],value=row[4])
        print('a')

    columns = ["invested", "value"]
    
    folio_qs = db.session.query(FolioValue).with_entities(FolioValue.date,func.sum(FolioValue.invested), func.sum(FolioValue.value)).filter(FolioValue.folio == Folio.number, Folio.portfolio_id == portfolio_id).filter(FolioValue.date >= from_date_min).group_by(FolioValue.date)

    portfolio_df = pd.DataFrame(data=folio_qs.all(), columns=["date"] + columns)
    portfolio_df.set_index("date",inplace=True)
    portfolio_df['portfolio_id'] = portfolio_id

    for row in folio_qs.all():
        updated_portfolio_value = get_or_create(db.session, PortfolioValue, date=row[0],invested=row[1],value=row[2],portfolio_id=portfolio_id)

    logger.info('updated portfolio')
    return 'scheme'


def update_nav(db,scheme_list):
    today = datetime.date.today()
    for id in scheme_list:
        current_folio_scheme = db.session.query(FolioScheme.id,FolioScheme.scheme,FundScheme.amfi_code).filter(FolioScheme.id==id).filter(FolioScheme.scheme==FundScheme.id).first()
        folo_scheme_id = current_folio_scheme[0]
        code = current_folio_scheme[2]

        if code is None:
            logger.info('"Unable to lookup code for %s" % code')
            continue
        nav = NAVHistory.query.filter_by(scheme=folo_scheme_id).order_by(desc("date")).first()
        if nav is not None:
            from_date = nav.date
        else:
            from_date = datetime.date(1970,1,1)
        if from_date == today:
            logger.info("Nav for %s is updated, skipping",code)
            continue
        logger.info("Fetching NAV for %s from %s", code, from_date.isoformat())
        mfapi_url = f"https://api.mfapi.in/mf/{code}"
        response = requests.get(mfapi_url, timeout=60)
        data = response.json()
        for item in reversed(data["data"]):
            date = date_parse(item["date"], dayfirst=True).date()
            if date <= from_date:
                continue
            try:
                nav_history = NAVHistory(scheme=folo_scheme_id,date=date, nav=item["nav"])
                db.session.add(nav_history)
            except:
                logger.info("error adding nav to")
        time.sleep(2)
    db.session.flush()
    db.session.commit()
    logger.info("Finished adding transactions")


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