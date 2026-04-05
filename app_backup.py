from flask import Flask
from services import db
from routers import api_blueprint
from flask_cors import CORS  
from flask_migrate import Migrate

app = Flask(__name__)
CORS(app)

# Подключение к локальному PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://aituproject_user:12345@localhost:5432/aituproject'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'connect_args': {'options': '-c timezone=Asia/Almaty'}
}

db.init_app(app)
migrate = Migrate(app, db)

app.register_blueprint(api_blueprint)

if name == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)