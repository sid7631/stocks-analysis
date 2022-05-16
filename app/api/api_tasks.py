import datetime
from itertools import groupby
from dateutil.parser import parse as dateparse
from datetime import date, timedelta
from tablib import Dataset

from sqlalchemy import asc, desc
from app.app_config import db
from decimal import Decimal
from collections import deque
from app.api.models import Folio, FolioScheme, FolioValue, NAVHistory, Portfolio, SchemeValue, Transaction

from typing import Optional, Union
import pandas as pd
import numpy as np
from sqlalchemy.dialects.sqlite import insert


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

def update_portfolio_value(start_date=None, portfolio_id=None, scheme_dates=None):
    if not isinstance(scheme_dates, dict):
        scheme_dates = {}
    # today = datetime.datetime.now(datetime.timezone.utc)
    today = datetime.date.today()

    from_date1 = today
    if len(scheme_dates) > 0:
        from_date1 = min(scheme_dates.values())
        if isinstance(from_date1, str):
            from_date1 = dateparse(from_date1).date()
    from_date2 = today
    if isinstance(start_date, str) and start_date != "auto":
        from_date2 = dateparse(start_date).date()
    elif isinstance(start_date, date):
        from_date2 = start_date
    else:
        qs = db.session.query(SchemeValue,FolioScheme,  Folio).filter(SchemeValue.scheme==FolioScheme.scheme).filter(FolioScheme.folio==Folio.number).filter(Folio.portfolio==portfolio_id).order_by(asc("date")).first()
        if qs.SchemeValue.date is not None:
            from_date2 = qs.SchemeValue.date 
    
    start_date = min(from_date1, from_date2)

    if portfolio_id is not None:
        qs = db.session.query(FolioScheme,Folio).filter(FolioScheme.folio==Folio.number).filter(Folio.portfolio==portfolio_id)
    
    if qs is None:
        qs = db.session.query(FolioScheme).all()
    from_date_min = today
    schemes = qs.all()
    dfs = []

    for i in schemes:
        print(i)
        scheme = FolioScheme.query.filter_by(id=i.FolioScheme.id).first()
        
        frm_date = scheme_dates.get(i.FolioScheme.id, start_date)

        if isinstance(frm_date, str):
            frm_date = dateparse(frm_date).date()
        
        scheme_val: SchemeValue = SchemeValue.query.filter(SchemeValue.id==i.FolioScheme.id, SchemeValue.date < frm_date).order_by(desc("date")).first()
        

        old_txns = Transaction.query.filter(Transaction.scheme==scheme.scheme, Transaction.date<frm_date).order_by(asc("date")).all()
        

        new_txns = Transaction.query.filter(Transaction.scheme==scheme.scheme, Transaction.date>=frm_date).order_by(asc("date")).all()
        

        from_date = None

        if scheme_val is not None:
            from_date = scheme_val.date
        if len(new_txns) > 0:
            from_date  = min(from_date or new_txns[0].date, new_txns[0].date)
        elif scheme_val is None or scheme_val.balance <= 1e-3:
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
            latest_nav = NAVHistory.query.filter_by(scheme=i.FolioScheme.scheme).order_by(desc("date")).first()
            to_date = latest_nav.date if latest_nav is not None else (today - timedelta(days=1))
        elif len(dates) > 0:
            to_date = dates[-1]
        else:
            print("Skipping scheme :: %s", i.FolioScheme.scheme)
            continue

        scheme_transactions = pd.DataFrame(
            data={"invested": invested, "avg_nav": average, "balance": balance}, index=dates
        )

        from_date_min = min(from_date, from_date_min)

        index = pd.date_range(from_date, to_date)
        scheme_vals = pd.DataFrame(
            data=[[np.nan] * len(columns)] * len(index), index=index, columns=columns
        )

        # if to_date != today:
            # pass
            # SchemeValue.query.filter(SchemeValue.scheme==i.FolioScheme.scheme, SchemeValue.date>to_date).delete()
            # FolioValue.query.filter(folio__schemes__id=scheme_id, date__gt=to_date).delete()
            # PortfolioValue.objects.filter(
            #     portfolio__folios__schemes__id=scheme_id, date__gt=to_date
            # ).delete()

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

        qs = NAVHistory.query.with_entities(NAVHistory.date, NAVHistory.nav).filter(NAVHistory.scheme==i.FolioScheme.scheme, NAVHistory.date >= from_date,  NAVHistory.date <=to_date).all()

        print(qs)
        nav_df = pd.DataFrame(data=qs, columns=["date", "nav"])
        nav_df.set_index("date", inplace=True)
        scheme_vals.loc[nav_df.index, ["nav"]] = nav_df
        scheme_vals.ffill(inplace=True)
        scheme_vals.fillna(value=0, inplace=True)
        scheme_vals["value"] = scheme_vals["nav"] * scheme_vals["balance"]
        scheme_vals["scheme"] = i.FolioScheme.scheme
        scheme_vals['scheme_id'] = i.FolioScheme.id
        scheme_vals = scheme_vals.reset_index().rename(columns={"index": "date"})
        dfs.append(scheme_vals)
    if len(dfs) == 0:
        print("No data found. Exiting..")
        return
    final_df = pd.concat(dfs)
    print(f"SchemeValue :: {len(final_df)} rows")
    dataset = Dataset().load(final_df)
    for row in final_df.to_records():
        insert_stmt = insert(SchemeValue).values(date=datetime.datetime.strptime(str(row[1])[:10],"%Y-%m-%d"),invested=row[2],avg_nav=row[3],balance=row[4],nav=row[5],value=row[6],scheme=row[7],scheme_id=row[8].item())
        do_update_stmt = insert_stmt.on_conflict_do_update(index_elements=['scheme_id','date'],set_=dict(date=datetime.datetime.strptime(str(row[1])[:10],"%Y-%m-%d"),invested=row[2],avg_nav=row[3],balance=row[4],nav=row[5],value=row[6],scheme=row[7],scheme_id=row[8].item()))
        db.session.execute(do_update_stmt)
    db.session.commit()

    columns = ["invested", "value", "avg_nav", "nav", "balance", "scheme_id", "scheme"]

    # svs = SchemeValue.query.filter(date >= from_date_min)
    svs = db.session.query(SchemeValue,FolioScheme,  Folio).with_entities(SchemeValue.date,SchemeValue.invested, SchemeValue.value, SchemeValue.avg_nav, SchemeValue.nav, SchemeValue.balance, SchemeValue.scheme_id, SchemeValue.scheme).filter(SchemeValue.date >= from_date_min)
    
    if portfolio_id is not None:
        svs = svs.filter(SchemeValue.scheme==FolioScheme.scheme).filter(FolioScheme.folio==Folio.number).filter(Folio.portfolio==portfolio_id)

    print(svs.all())
    sval_df = pd.DataFrame(data=svs.all(), columns=["date"] + columns)
    sval_df.set_index("date",inplace=True)

    dfs=[]

    for scheme_id, group in sval_df.groupby('scheme_id'):
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
        merged_df["scheme_id"] = merged_df["scheme_id"].astype("int")
        # merged_df["scheme__folio_id"] = merged_df["scheme__folio_id"].astype("int")

        merged_df = merged_df.reset_index().rename(
            columns={"index": "date", "scheme_id": "folio_id"}
        )
        merged_df = (
            merged_df.groupby(["date", "folio_id"])[["invested", "value"]].sum().reset_index()
        )
        # folio_dataset = Dataset().load(merged_df)
        # fv_resource = FolioValueResource()

        # result = fv_resource.import_data(folio_dataset, dry_run=False)
        # if result.has_errors():
        #     for row in result.rows[:10]:
        #         for error in row.errors:
        #             print(error.error, error.traceback)
        # else:
        #     logger.info("Import success! :: %s", str(result.totals))



    print(' ')

