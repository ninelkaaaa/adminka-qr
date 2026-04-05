# manage.py
import sys
import os

# Добавляем корень проекта в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from services import db
from flask_migrate import Migrate

migrate = Migrate(app, db)

# Теперь команды flask db будут работать

