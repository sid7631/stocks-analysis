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
from app.api.models import  AMC, Folio, Portfolio, FolioScheme, FolioValue, FundScheme, NAVHistory, PortfolioValue, SchemeValue, Transaction
from app.api.utils import get_or_create, insert_or_update
import numpy as np
from sqlalchemy.sql import func
from app.app_config import db
from app.tasks import fetch_nav, create_task, get_task_status

logger = logging.getLogger(__name__)





# def import_cas(data: CASParserDataType, user_id):


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

        # details for folio update
        amc = (row.get("amc") or "").strip()
        pan = (row.get("PAN") or "").strip()
        kyc = (row.get("KYC") or "").strip()
        pankyc = (row.get("PANKYC") or "").strip()
        number = (row.get("folio") or "").split('/')[0].strip()
        schemes: List[SchemeType] = row.get("schemes",[]) or []

        #create amc
        amc = get_or_create(db.session,AMC,name=amc)
        #create folio
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

    fetch_task = fetch_nav.delay(
            fund_schemes_list=list(fund_schemes_list),
            update_portfolio_kwargs={
                "from_date": "auto",
                "portfolio_id": portfolio.id,
                "scheme_dates": scheme_dates,
            }
        )
    
    # get_task_status(fetch_task.task_id)
    # fetch_task.wait()

    result = {
        "task_id": fetch_task.task_id,
        "task_status": get_task_status(fetch_task.task_id).status,
        "task_result": get_task_status(fetch_task.task_id).result
    }

    return result
