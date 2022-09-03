from app.api.models import Portfolio, PortfolioValue
from sqlalchemy import desc, cast, String, Numeric, Float


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

    resp = {
        'summary': summary,
        'performance':performance
    }


    return resp
