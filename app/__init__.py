import os
import mysql.connector
from flask import Flask
from dotenv import load_dotenv

load_dotenv()

def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_NAME", "backup_registry"),
        user=os.getenv("DB_USER", "backup_app"),
        password=os.getenv("DB_PASSWORD", ""),
    )

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-only-change-me")
    from .routes import bp
    app.register_blueprint(bp)
    return app
