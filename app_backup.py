import os
from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate

from services import db
from routers import api_blueprint

app = Flask(__name__)
CORS(app)

# 🔥 Берём DATABASE_URL из Railway ENV
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL не найден в переменных окружения")

# 🔗 Подключение к PostgreSQL (Railway)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ⏰ timezone (безопасный вариант для Railway)
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'connect_args': {'options': '-c timezone=Asia/Almaty'}
}

# init DB
db.init_app(app)
migrate = Migrate(app, db)

# routes
app.register_blueprint(api_blueprint)

# ✔️ правильный entry point
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)