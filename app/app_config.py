from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from pathlib import Path



db = SQLAlchemy()
migrate = Migrate()

def create_folder(path):
    Path(path).mkdir(parents=True, exist_ok=True)


