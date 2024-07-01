from flask import Blueprint

# Создаем Blueprint для основных маршрутов
main_bp = Blueprint('main', __name__)

from app.main import routes
