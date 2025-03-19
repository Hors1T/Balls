from flask import Flask
from config import Config
from db import db
from flask_login import LoginManager
from routes import app_routes
from flask_migrate import Migrate
from models import User
app = Flask(__name__)
app.config.from_object(Config)

# Подключение базы данных
db.init_app(app)
migrate = Migrate(app, db)
# Настройка Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
# Регистрация маршрутов
app.register_blueprint(app_routes)

if __name__ == "__main__":
    app.run(debug=True)