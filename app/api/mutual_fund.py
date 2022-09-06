from app.api.models import Folio, FolioScheme, FolioValue, FundScheme, Portfolio, PortfolioValue, SchemeValue
from sqlalchemy import desc, cast, String, Numeric, Float, func, and_
from app.app_config import db
import pandas as pd
import json

def mutual_fund_summary(user_id):
    portfolio = Portfolio.query.filter_by(user=user_id).first()
    if portfolio is None:
        return 'Mutual Funds data absent'
    
    portfolio_value = PortfolioValue.query.filter_by(portfolio_id=portfolio.id).order_by(desc("date")).limit(2).all()

    summary = {
        'invested':portfolio_value[-1].invested,
        'value':portfolio_value[-1].value,
        'day_change':portfolio_value[-1].value - portfolio_value[-2].value,
        'day_change_perc':((portfolio_value[-1].value - portfolio_value[-2].value)/portfolio_value[-2].value)*100,
        'total_return' : portfolio_value[-1].value - portfolio_value[-1].invested,
        'xirr_perc':None,
        'last_updated':portfolio_value[-1].date
    }

    performance_query = PortfolioValue.query.with_entities(PortfolioValue.date,cast(PortfolioValue.value, Float)).filter_by(portfolio_id=1).order_by("date")
    performance = [ [int(x.strftime("%s"))*1000, y] for x,y in performance_query ]


    #get schemevalue summary
    subq = db.session.query(
        SchemeValue.scheme,
        func.max(SchemeValue.date).label('maxdate')
    ).group_by(SchemeValue.scheme).subquery('t2')

    query = db.session.query(FundScheme.name,FundScheme.amc,FundScheme.isin, FundScheme.category, FundScheme.plan, Folio.number, SchemeValue.scheme, SchemeValue.avg_nav, SchemeValue.nav, SchemeValue.balance, SchemeValue.date, SchemeValue.invested, SchemeValue.value).join(
        subq,
        and_(
            SchemeValue.scheme == subq.c.scheme,
            SchemeValue.date == subq.c.maxdate
        )
    ).join(FolioScheme).filter(FolioScheme.id==SchemeValue.scheme).join(Folio).filter(
        Folio.number==FolioScheme.folio, Folio.portfolio_id==portfolio.id
    ).join(FundScheme).filter(
        FundScheme.id == FolioScheme.scheme
    )
    scheme_value_summary = pd.read_sql(query.statement, query.session.bind)
    scheme_value_summary = scheme_value_summary.groupby(['name','isin']).agg({'balance':'sum','invested':'sum','value':'sum','nav':'mean'}).reset_index().sort_values(by=['value'],ascending=False)
    scheme_value_summary['avg_nav'] = scheme_value_summary['invested']/scheme_value_summary['balance']
    scheme_value_summary['profit'] = scheme_value_summary['value']-scheme_value_summary['invested']
    scheme_value_summary = scheme_value_summary.round(decimals = 0)
    scheme_value_summary = scheme_value_summary.to_json(orient='records')

    resp = {
        'summary': summary,
        'performance':performance,
        'funds':json.loads(scheme_value_summary)
    }


    return resp


def amc_summary(user_id,isin):
    portfolio = Portfolio.query.filter_by(user=user_id).first()
    if portfolio is None:
        return 'Mutual Funds data absent'


    subq = db.session.query(
    SchemeValue.scheme,
        # func.max(SchemeValue.date).label('maxdate')
    ).group_by(SchemeValue.scheme).subquery('t2')

    query = db.session.query(FundScheme.name,Folio.amc, Folio.number, SchemeValue.scheme, SchemeValue.avg_nav, SchemeValue.nav, SchemeValue.balance, SchemeValue.date, SchemeValue.invested, SchemeValue.value).join(
        subq,
        and_(
            SchemeValue.scheme == subq.c.scheme,
            # SchemeValue.date == subq.c.maxdate
        )
    ).join(FolioScheme).filter(FolioScheme.id==SchemeValue.scheme).join(Folio).filter(
        Folio.number==FolioScheme.folio, Folio.portfolio_id==portfolio.id
    ).join(FundScheme).filter(
        FundScheme.id == FolioScheme.scheme,
        FundScheme.isin == isin
    )

    performance = pd.read_sql(query.statement, query.session.bind)
    performance = performance.groupby(['name','date']).sum().reset_index()
    performance = json.loads(performance[['date','value']].to_json(orient='values'))


    #get amc detailed performance
    subq = db.session.query(
        FolioValue.folio,
        func.max(FolioValue.date).label('maxdate')
    ).group_by(FolioValue.folio).subquery('t2')

    query = db.session.query(FundScheme.name, FundScheme.amc, FolioValue.folio, FundScheme.category, FundScheme.plan, FundScheme.isin , FolioValue.invested, FolioValue.value).join(
        subq,
        and_(
            FolioValue.folio == subq.c.folio,
            FolioValue.date == subq.c.maxdate
        )
    ).join(Folio).filter(
        FolioValue.folio == Folio.number,
        Folio.amc == FundScheme.amc,
        FundScheme.isin == isin,
        Folio.portfolio_id == portfolio.id
    )

    fund_summary = pd.read_sql(query.statement, query.session.bind)
    fund_summary['profit'] = fund_summary['value'] - fund_summary['invested']
    folio_summary = json.loads(fund_summary.to_json(orient='records'))

    fund_summary_detail = fund_summary.groupby(['name', 'amc', 'isin', 'category', 'plan']).sum().reset_index()
    fund_summary_detail = json.loads(fund_summary_detail.to_json(orient='records'))[0]


    resp = {
        'performance': performance,
        'summary' : fund_summary_detail,
        'folio_summary':folio_summary,
    }

    return resp
