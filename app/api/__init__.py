from flask import Blueprint

# Создаем Blueprint для основных маршрутов
api_bp = Blueprint('api', __name__)

from app.api import routes
