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

logger = logging.getLogger(__name__)


def import_cas(data: CASParserDataType, user_id, db):

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
            for txn in transactions:
                if txn["balance"] is None:
                    txn["balance"] = balance
                else:
                    balance = txn["balance"]
                    txn_date = txn["date"]
                    if txn_date <= latest_transaction_date:
                        continue
                    transaction = get_or_create(db.session, Transaction, scheme=folio_scheme.id, date=txn_date, balance=balance, units=txn["units"],description=txn["description"], amount=txn["amount"], nav=txn["nav"], order_type=Transaction.get_order_type(txn["description"], txn["amount"]), sub_type=txn["type"])
                    
                    if folio_scheme.id not in schemes_list:
                        schemes_list.add(folio_scheme.id)
                    if folio.number not in folios_list:
                        folios_list.add(folio.number)
            
            if fund_scheme.id not in fund_schemes_list:
                fund_schemes_list.add(fund_scheme.id)
    
    update_nav(db, fund_schemes_list)
    update_scheme_value(db,portfolio.id)
    update_folio_value(db,portfolio.id)
    update_portfolio_value(db,portfolio.id)
    return 'ok'

def update_portfolio_value(db,portfolio_id):
    today = datetime.date.today()
    columns = ["invested", "value"]
    portfolio_value: PortfolioValue = PortfolioValue.query.filter_by(portfolio_id=portfolio_id).order_by(desc("date")).first()
    if portfolio_value is not None:
        from_date = portfolio_value.date
    else:
        from_date = datetime.date(1970,1,1)
    qs = FolioValue.query.with_entities(FolioValue.date,func.sum(FolioValue.invested), func.sum(FolioValue.value)).filter(FolioValue.folio == Folio.number, Folio.portfolio_id == portfolio_id).filter(FolioValue.date >= from_date).group_by(FolioValue.date)

    # portfolio_df = pd.DataFrame(data=qs.all(), columns=["date"] + columns)
    # portfolio_df.set_index("date",inplace=True)
    # portfolio_df['portfolio_id'] = portfolio_id

    for row in qs.all():
        portfolio_value_update = get_or_create(db.session, PortfolioValue, date=row[0],invested=row[1],value=row[2],portfolio_id=portfolio_id)


    print('ok')


def update_folio_value(db, portfolio_id, folios_list=None):
    today = datetime.date.today()
    # qs = SchemeValue.query.filter(SchemeValue.scheme==FolioScheme.id,FolioScheme.folio==Folio.number,Folio.portfolio_id==portfolio_id).all()
    qs = Folio.query.filter(Folio.portfolio_id==portfolio_id).all()
    from_date_min = today
    dfs = []
    for folio in qs:
        print(folio)
        folio_value: FolioValue = FolioValue.query.filter_by(folio=folio.number).order_by(desc("date")).first()
        if folio_value is not None:
            from_date = folio_value.date
        else:
            from_date = datetime.date(1970,1,1)
        print(from_date)

        qs = SchemeValue.query.with_entities(SchemeValue.date,SchemeValue.invested, SchemeValue.value, SchemeValue.avg_nav, SchemeValue.nav, SchemeValue.balance, SchemeValue.scheme).filter(SchemeValue.scheme==FolioScheme.id).filter(FolioScheme.folio==folio.number).filter(SchemeValue.date > from_date)

        columns = ["invested", "value", "avg_nav", "nav", "balance", "scheme"]

        df = pd.DataFrame(data=qs.all(), columns=["date"] + columns)
        rows, _ = df.shape
        if rows == 0:
            continue

        df.set_index("date",inplace=True)
        df["folio"] = folio.number

        dfs.append(df)

    if len(dfs) > 0:
        merged_df = pd.concat(dfs)
        merged_df["scheme"] = merged_df["scheme"].astype("int")
        # merged_df["folio_number"] = merged_df["folio_number"].astype("int")

        merged_df = merged_df.reset_index().rename(
            columns={"index": "date", "folio": "folio"}
        )
        merged_df = (
            merged_df.groupby(["date", "folio"])[["invested", "value"]].sum().reset_index()
        )    

        for row in merged_df.to_records():
            updated_folio_value = get_or_create(db.session,FolioValue,date=datetime.datetime.strptime(str(row[1])[:10],"%Y-%m-%d"),folio=row[2],invested=row[3],value=row[4])
    

    print('ok')

def update_scheme_value(db,portfolio_id, schemes_list=None):
    today = datetime.date.today()
    # if isinstance(scheme_ids, list):
    qs = FolioScheme.query.filter(FolioScheme.folio==Folio.number,Folio.portfolio_id==portfolio_id).all()
    # qs = db.session.query(SchemeValue).filter(SchemeValue.scheme==FolioScheme.id).all()
    from_date_min = today
    dfs=[]
    for folio_scheme in qs:
        scheme_value: SchemeValue = SchemeValue.query.filter_by(scheme=folio_scheme.id).order_by(desc("date")).first()
        
        if scheme_value is not None:
            from_date = scheme_value.date
        else:
            from_date = datetime.date(1970,1,1)

        old_txns = Transaction.query.filter(Transaction.scheme==folio_scheme.id, Transaction.date <= from_date).order_by(asc("date")).all()
        new_txns = Transaction.query.filter(Transaction.scheme==folio_scheme.id, Transaction.date > from_date).order_by(asc("date")).all()

        if len(new_txns) > 0:
            from_date = new_txns[0].date
        else:
            logger.info("Ignoring folio_scheme with id :: %s", folio_scheme.id)
            continue
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
            latest_nav = NAVHistory.query.filter_by(scheme=folio_scheme.scheme).order_by(desc("date")).first()
            to_date = latest_nav.date if latest_nav is not None else (today - datetime.timedelta(days=1))
        elif len(dates) > 0:
            to_date = dates[-1]
        else:
            print("Skipping scheme :: %s",folio_scheme.id)
            continue
    
        scheme_transactions = pd.DataFrame(
            data={"invested": invested, "avg_nav": average, "balance": balance}, index=dates
        )

        from_date_min = min(from_date, from_date_min)

        index = pd.date_range(from_date , to_date)

        scheme_values = pd.DataFrame(
            data=[[np.nan] * len(columns)] * len(index), index=index, columns=columns
        )

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

        qs = NAVHistory.query.with_entities(NAVHistory.date, NAVHistory.nav).filter(NAVHistory.scheme==folio_scheme.scheme, NAVHistory.date >= from_date,  NAVHistory.date <=to_date).all()
        nav_df = pd.DataFrame(data=qs, columns=["date", "nav"])
        nav_df.set_index("date", inplace=True)
        # nav_df = nav_df["nav"].astype(float)
        scheme_values.loc[nav_df.index, ["nav"]] = nav_df
        scheme_values.ffill(inplace=True)
        scheme_values.fillna(value=0, inplace=True)
        scheme_values["value"] = scheme_values["nav"] * scheme_values["balance"]
        scheme_values["scheme"] = folio_scheme.id
        scheme_values = scheme_values.reset_index().rename(columns={"index": "date"})
        dfs.append(scheme_values)
    
    if len(dfs) == 0:
        logger.info("No data found. exiting..")
        return
    final_df = pd.concat(dfs)
    logger.info(f"SchemeValue :: {len(final_df)} rows")
    for row in final_df.to_records():
        updated_scheme_value = get_or_create(db.session, SchemeValue, date=datetime.datetime.strptime(str(row[1])[:10],"%Y-%m-%d"),invested=row[2],avg_nav=row[3],balance=row[4],nav=row[5],value=row[6],scheme=int(row[7]))


    print('ok')

def update_nav(db,fund_schemes_list):
    today = datetime.date.today()
    fund_schemes = FundScheme.query.filter(FundScheme.id.in_(list(fund_schemes_list))).all()
    for fund_scheme in fund_schemes:
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