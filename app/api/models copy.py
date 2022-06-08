from tokenize import String

from django.forms import DateField
from app.app_config import db
import enum

from sqlalchemy_utils.types.choice import ChoiceType

class Base(db.Model):

    __abstract__  = True

    id            = db.Column(db.Integer, primary_key=True)
    date_created  = db.Column(db.DateTime,  default=db.func.current_timestamp())
    date_modified = db.Column(db.DateTime,  default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

class Holdings(Base):

    __tablename__ = 'holdings'

    #Symbol
    symbol = db.Column(db.String(256), nullable = False)
    #Sector
    sector = db.Column(db.String(256), nullable = False)
    #Quantity
    quantity = db.Column(db.Integer, nullable=False)
    #Average Price
    price = db.Column(db.Float, nullable=False)


class Portfolio(Base):
    """User Portfolio"""
    __tablename__ = 'portfolio'

    user = db.Column(db.Integer,db.ForeignKey('auth_user.id'), nullable=False)
    name= db.Column(db.String(128),  nullable=False)
    email = db.Column(db.String(128),  nullable=False,unique=True)
    pan = db.Column(db.String(10),  nullable=True,unique=True)

    def __init__(self, user, name,email, pan) -> None:
       self.user = user
       self.name = name
       self.email = email
       self.pan = pan

    def __repr__(self):
        return '<Portfolio %r>' % (self.name) 


class AMC(db.Model):
    """Mutual Fund Asset Management Company (AMC)"""
    __tablename__ = 'amc'


    code = db.Column(db.String(64), unique=True,primary_key=True)
    name = db.Column(db.String(128), unique=True)
    description = db.Column(db.String(2024),nullable=True)
    

    def __init__(self,name,code,description=None):
        self.name = name
        self.code = code
        if description:
            self.description = description

    def __repr__(self):
        return self.name

    # class Meta:
    #     verbose_name = "AMC"
    #     verbose_name_plural = "AMCs"


class FundCategory(Base):
    """Fund Category (EQUITY, DEBT etc)"""

    __tablename__ = 'fund_category'

    class MainCategory(enum.Enum):
        EQUITY = "EQUITY"
        DEBT = "DEBT"
        HYBRID = "HYBRID"
        OTHER = "OTHER"

    type = db.Column(ChoiceType(MainCategory), default=MainCategory.EQUITY)
    subtype = db.Column(db.String(64))

    def __repr__(self):
        return f"{self.type} - {self.subtype}"

    # class Meta:
    #     verbose_name = "FundCategory"
    #     verbose_name_plural = "Fund Categories"

class FundScheme(db.Model):
    """Mutual fund schemes"""
    __tablename__ = 'fund_scheme'

    TYPES = [
        'REGULAR','DIRECT'
    ]

    # id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(512), index=True, primary_key=True)
    amc = db.Column(db.String(128), db.ForeignKey('amc.code',ondelete='CASCADE'), primary_key=True)
    rta = db.Column(db.String(12), nullable=True)
    category = db.Column( db.ForeignKey('fund_category.id',ondelete='RESTRICT'), nullable=True)
    plan = db.Column(db.String(8),  default=TYPES[1],primary_key=True)
    rta_code = db.Column(db.String(32))
    amfi_code = db.Column(db.String(8), nullable=True, index=True,primary_key=True)
    isin = db.Column(db.String(16), index=True)

    def __init__(self, name,amc,rta,category,plan,rta_code,amfi_code,isin):
        self.name = name
        self.amc = amc
        self.rta = rta
        self.category = category
        self.plan = plan
        self.rta_code = rta_code
        self.amfi_code = amfi_code
        self.isin = isin

    def __repr__(self):
        return f"{self.name} - {self.plan}"

    @classmethod
    def get_fund_plan(cls, amc_name):
        if 'regular' in amc_name.lower():
            return cls.TYPES[0]
        elif 'direct' in amc_name.lower():
            return cls.TYPES[1]

class Folio(db.Model):
    """Mutual Fund Folio"""

    __tablename__ = 'folio'

    amc = db.Column(db.String(128), db.ForeignKey('amc.code',ondelete='RESTRICT'))
    portfolio = db.Column(db.Integer, db.ForeignKey('portfolio.id',ondelete='CASCADE'))
    number = db.Column(db.String(128), unique=True, primary_key=True)
    pan = db.Column(db.String(10), nullable=True)
    kyc = db.Column(db.Boolean,default=False)
    pan_kyc = db.Column(db.Boolean,default=False)

    # def __repr__(self):
    #     return f"{self.portfolio.name} - {self.number}"

    def __init__(self, amc, portfolio, number, pan, kyc, pan_kyc):
        self.amc = amc
        self.portfolio = portfolio
        self.number = number
        self.pan = pan
        self.kyc = kyc
        self.pan_kyc = pan_kyc

class FolioScheme(Base):
    """Track schemes inside a folio"""

    __tablename__ = 'folio_scheme'

    scheme = db.Column(db.String(8),  db.ForeignKey('fund_scheme.amfi_code',ondelete='CASCADE'))
    folio = db.Column(db.String(128),  db.ForeignKey('folio.number',ondelete='CASCADE'))
    valuation = db.Column(db.Numeric(20,2), nullable=True)
    xirr = db.Column(db.Numeric(20,4),  nullable=True)
    valuation_date = db.Column(db.Date, nullable=True)
    # created  = db.Column(db.DateTime,  default=db.func.current_timestamp())
    # modified = db.Column(db.DateTime,  default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def __init__(self, scheme, folio, valuation, valuation_date,xirr=None):
        self.scheme = scheme
        self.folio = folio
        self.valuation = valuation
        self.xirr = xirr
        self.valuation_date = valuation_date

    # def __repr__(self):
    #     return f"{self.scheme} - {self.folio}"

class Transaction(Base):
    """Transactions inside a folio scheme"""
    __tablename__ = 'transaction'

    class OrderType(enum.Enum):
        BUY = "Buy"
        REINVEST = "Reinvest"
        REDEEM = "Redeem"
        SWITCH = "Switch"

    scheme = db.Column(db.String(8), db.ForeignKey('folio_scheme.scheme',ondelete='CASCADE'))
    date = db.Column(db.Date)
    description = db.Column(db.String(2024),nullable=True)
    order_type = db.Column(ChoiceType(OrderType))
    sub_type = db.Column(db.String(32), nullable=True)
    amount = db.Column(db.Numeric(20,2))
    nav = db.Column(db.Numeric(15,4))
    units = db.Column(db.Numeric(20,3))
    balance = db.Column(db.Numeric(40,3))

    @classmethod
    def get_order_type(cls, description, amount):
        if "switch" in description.lower():
            return cls.OrderType.SWITCH
        elif amount > 0:
            if "reinvest" in description.lower():
                return cls.OrderType.REINVEST
            return cls.OrderType.BUY
        return cls.OrderType.REDEEM

    # def __init__(self,scheme, date, description,):
    #     pass

    def __repr__(self):
        return f"{self.order_type} @ {self.amount} for {self.units} units"

class DailyValue(db.Model):
    """Track daily total of amount invested per scheme/folio/portfolio"""

    __abstract__  = True

    date = db.Column(db.Date,index=True)
    invested = db.Column(db.Numeric(30,2))
    value = db.Column(db.Numeric(30,2))

class SchemeValue(DailyValue):

    id = db.Column(db.Integer, primary_key=True)
    scheme_id = db.Column(db.String(128), db.ForeignKey('folio_scheme.folio'),)
    scheme = db.Column(db.String(8), db.ForeignKey('folio_scheme.scheme',ondelete='CASCADE'))
    avg_nav = db.Column(db.Numeric(30,10), default=0.0)
    nav = db.Column(db.Numeric(15,4))
    balance = db.Column(db.Numeric(20,3))

    __table_args__ = (db.UniqueConstraint('scheme_id', 'date'),)

    # def __init__(self, scheme_id, scheme, nav, balance):
        # self.scheme_id = scheme_id
        # self.scheme = scheme
        # # self.avg_nav = avg_nav
        # self.nav = nav
        # self.balance = balance


class FolioValue(DailyValue):

    __table_args__ = (db.UniqueConstraint('folio', 'date'),)

    id = db.Column(db.Integer, primary_key=True)
    folio = db.Column(db.String(128),  db.ForeignKey('folio.number',ondelete='CASCADE'))

class PortfolioValue(DailyValue):

    __table_args__ = (db.UniqueConstraint('portfolio', 'date'),)

    id = db.Column(db.Integer, primary_key=True)
    portfolio = db.Column(db.Integer, db.ForeignKey('portfolio.id',ondelete='CASCADE'))
    xirr = db.Column(db.Numeric(30,2), nullable=True)
    live_xirr = db.Column(db.Numeric(30,2), nullable=True)

class NAVHistory(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    scheme = db.Column(db.String(8),  db.ForeignKey('folio_scheme.folio',ondelete='CASCADE'))
    date = db.Column(db.Date)
    nav = db.Column(db.Numeric(15,4))

    __table_args__ = (db.UniqueConstraint('scheme', 'date'),)