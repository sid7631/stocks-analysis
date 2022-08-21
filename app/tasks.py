import datetime
import os
import time
from dateutil.parser import parse as date_parse
from sqlalchemy.exc import IntegrityError
from sqlalchemy import desc

from celery import Celery
import requests
from requests.exceptions import RequestException, Timeout
import logging

from kombu.serialization import registry
from app.api.models import  AMC, Folio, Portfolio, FolioScheme, FolioValue, FundScheme, NAVHistory, PortfolioValue, SchemeValue, Transaction

from app.api.utils import get_or_create, insert_or_update, update_portfolio_value

# from app.api.models import FolioScheme, NAVHistory
# from app.api.api_tasks import update_portfolio_value

from app.app_config import db
# from app.api.casimoprter import update_portfolios

celery = Celery(__name__)
celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
celery.conf.result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
celery.conf.accept_content = ['application/text','json']

registry.enable('json')
registry.enable('application/text')

logger = logging.getLogger(__name__)

@celery.task(name="create_task")
def create_task(task_type):
    time.sleep(int(task_type) * 10)
    return True


@celery.task(
    name="NAVFetcher",
    # serializer="pickle"
    # autoretry_for=(RequestException, Timeout),
    # retry_backoff=60 * 60,
    # retry_backoff_max=5 * 60 * 60,
    # default_retry_delay=30 * 60,
    # retry_kwargs={"max_retries": 6},
)
def fetch_nav(fund_schemes_list=None,update_portfolio_kwargs=None):
    logger.info('fetch nav called with task')
    print('fetch_nav running')
    print(fund_schemes_list,update_portfolio_kwargs)
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
    
    # update_portfolios(**kwargs)
    print(kwargs)
    update_portfolios.delay(**kwargs)
    return {"status": True}

@celery.task(
    name="UpdatePortfolio",
    # serializer="pickle"
    # autoretry_for=(RequestException, Timeout),
    # retry_backoff=60 * 60,
    # retry_backoff_max=5 * 60 * 60,
    # default_retry_delay=30 * 60,
    # retry_kwargs={"max_retries": 6},
)
def update_portfolios(from_date = None, portfolio_id=None, scheme_dates=None):
    update_portfolio_value(start_date = from_date, portfolio_id=portfolio_id,scheme_dates=scheme_dates)
    return {"status": True}