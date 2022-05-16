import datetime
import os
import time
from dateutil.parser import parse as date_parse
from sqlalchemy.exc import IntegrityError
from sqlalchemy import desc

from celery import Celery
import requests
from requests.exceptions import RequestException, Timeout

from app.api.models import FolioScheme, NAVHistory
from app.api.api_tasks import update_portfolio_value

from app.app_config import db

celery = Celery(__name__)
celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
celery.conf.result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")


@celery.task(name="create_task")
def create_task(task_type):
    time.sleep(int(task_type) * 10)
    return True

# @celery.task(
#     bind=True,
#     name="NAVFetcher",
#     autoretry_for=(RequestException, Timeout),
#     retry_backoff=60 * 60,
#     retry_backoff_max=5 * 60 * 60,
#     default_retry_delay=30 * 60,
#     retry_kwargs={"max_retries": 6},
# )
def fetch_nav(scheme_ids=None, update_portfolio_kwargs=None):
    ## qs = FolioScheme
    # if isinstance(scheme_ids, list):
    #     qs = db.session.query(FolioScheme.scheme.distinct().label('scheme')).filter(FolioScheme.id.in_(scheme_ids)).order_by(FolioScheme.scheme).all()
    # folio_schemes = set(qs)
    # for sid in folio_schemes:
    #     code = sid.scheme
    #     if code is None:
    #         print('"Unable to lookup code for %s" % code')
    #         continue
    #     if code is not None:
    #         nav = NAVHistory.query.filter_by(scheme=code).order_by(desc("date")).first()
    #         if nav is not None:
    #             from_date = nav.date
    #             print("Fetching NAV for %s from %s", code, nav.date.isoformat())
    #         else:
    #             from_date = datetime.date(1970, 1, 1)
    #             print("Fetching NAV for %s from beginning", code)
    #         mfapi_url = f"https://api.mfapi.in/mf/{code}"
    #         response = requests.get(mfapi_url, timeout=60)
    #         data = response.json()
    #         for item in reversed(data["data"]):
    #             date = date_parse(item["date"], dayfirst=True).date()
    #             if date <= from_date:
    #                 continue
    #             try :
    #                 nav_history = NAVHistory(scheme=code, date=date, nav= item["nav"])
    #                 db.session.add(nav_history)
    #             except:
    #                 print('error')
                
    #         time.sleep(2)
    #     print(nav)
    # db.session.flush()
    # db.session.commit()
    kwargs = {}
    if isinstance(update_portfolio_kwargs, dict):
        kwargs.update(update_portfolio_kwargs)
    else:
        pass
    print(kwargs)
    print("Calling update portfolios with arguments %s", str(kwargs))
    # update_portfolios.delay(**kwargs)
    update_portfolios(**kwargs)
    
# @celery.task(
#     name="UpdatePortfolios",
# )
def update_portfolios(from_date=None, portfolio_id=None, scheme_dates=None):
    update_portfolio_value(
        start_date=from_date, portfolio_id=portfolio_id, scheme_dates=scheme_dates
    )