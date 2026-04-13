import os
from flask import Flask
from services import db
from routers import api_blueprint
from flask_cors import CORS
from flask_migrate import Migrate

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:12345@localhost:5432/aituproject"
)

db.init_app(app)
migrate = Migrate(app, db)
CORS(app)

app.register_blueprint(api_blueprint)

@app.route("/")
def home():
    return {"status": "ok"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))