from app.api.models import Portfolio
    # , PortfolioValue


def mutual_fund_summary(user_id):
    portfolio = Portfolio.query.filter_by(user=user_id).first()
    if portfolio is None:
        return 'Mutual Funds data absent'
    
    portfolio_value = PortfolioValue.query.filter_by(portfolio_id=portfolio.id).all()

    s = list(portfolio_value)

    return portfolio_value
