import os

class Config(object):
    # Statement for enabling the development environment
    DEBUG = True

    # Define the application directory

    BASE_DIR = os.path.abspath(os.path.dirname(__file__))  

    # Define the database - we are working with
    # SQLite for this example
    # SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'app.db')

    SQLALCHEMY_DATABASE_URI = "postgresql://postgres:postgres@localhost:5432/stocks_analysis"
    DATABASE_CONNECT_OPTIONS = {}
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Application threads. A common general assumption is
    # using 2 per available processor cores - to handle
    # incoming requests using one and performing background
    # operations using the other.
    THREADS_PER_PAGE = 2

    # Enable protection agains *Cross-site Request Forgery (CSRF)*
    CSRF_ENABLED     = True

    # Use a secure, unique and absolutely secret key for
    # signing the data. 
    CSRF_SESSION_KEY = "secret"

    # Secret key for signing cookies
    SECRET_KEY = "secret"

    static_folder = 'client/build'

    DATA_FOLDER = 'drive'

class ProductionConfig(Config):
    DATABASE_URI = 'mysql://user@localhost/foo'

class DevelopmentConfig(Config):
    CELERY_BROKER_URL='redis://localhost:6379',
    CELERY_RESULT_BACKEND='redis://localhost:6379'
    DEBUG = True

class TestingConfig(Config):
    TESTING = True