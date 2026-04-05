import os
from flask import Flask
from services import db
from routers import api_blueprint
from flask_cors import CORS
from flask_migrate import Migrate

app = Flask(__name__)

# --- DATABASE ---
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:12345@localhost:5432/aituproject"  # локальный fallback
)
# --- INIT ---
db.init_app(app)
migrate = Migrate(app, db)
CORS(app)

# --- ROUTES ---
app.register_blueprint(api_blueprint)

# --- TEST ROUTE ---
@app.route("/")
def home():
    return {"status": "ok", "message": "Server is running"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)