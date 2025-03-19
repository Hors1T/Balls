import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "supersecretkey"
    SQLALCHEMY_DATABASE_URI = "sqlite:///volleyball_store.db"  # Используем SQLite
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'static/images'
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}