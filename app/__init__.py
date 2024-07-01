import os
import logging
from logging.handlers import SMTPHandler, RotatingFileHandler

from flask import Flask
from config import Config
from flask_mail import Mail
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_babelex import Babel

from flask_apscheduler import APScheduler
from flask_compress import Compress

from flask_assets import Environment, Bundle

# Инициализация базы данных
db = SQLAlchemy()
migrate = Migrate()

babel = Babel()

login = LoginManager()
login.login_view = 'auth.login'
login.login_message = 'Для доступа к этой странице требуется авторизация.'
mail = Mail()

admin = Admin()

scheduler = APScheduler()
compress = Compress()


def create_app():
    app = Flask(__name__)
    app.config['DEBUG'] = True
    app.config.from_object(Config)
    app.config['DEBUG'] = True

    # При создании миграции не удалять таблицы с указанными именами
    def include_object(_object, name, type_, reflected, compare_to):
        if type_ == 'table' and name in ['layer', 'topology', 'spatial_ref_sys']:
            return False
        return True

    db.init_app(app)
    migrate.init_app(app, db, include_object=include_object)
    babel.init_app(app)
    login.init_app(app)
    mail.init_app(app)

    # Регистрация Blueprint'а для основных маршрутов
    from app.auth import auth_bp
    app.register_blueprint(auth_bp)
    from app.main import main_bp
    app.register_blueprint(main_bp)

    from app.api import api_bp
    app.register_blueprint(api_bp)

    admin.init_app(app)
    admin.template_mode = 'bootstrap3'

    from app.admin_panel import init_admin_views
    init_admin_views()

    scheduler.init_app(app)
    compress.init_app(app)

    assets = Environment(app)

    # Создаем Bundle для JavaScript файлов, которые мы хотим обфусцировать
    js = Bundle('js/base.js', filters='rjsmin', output='gen/packed.js')

    # Регистрируем Bundle в нашем Environment
    assets.register('js_all', js)

    # scheduler.api_enabled = True
    # from app.cron import create_schedule_tasks
    # create_schedule_tasks(app)

    scheduler.start()

    if not app.debug and not app.testing:
        if app.config['MAIL_SERVER']:
            auth = None
            if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
                auth = (app.config['MAIL_USERNAME'],
                        app.config['MAIL_PASSWORD'])
            secure = None
            if app.config['MAIL_USE_TLS']:
                secure = ()
            mail_handler = SMTPHandler(
                mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
                fromaddr='no-reply@' + app.config['MAIL_SERVER'],
                toaddrs=app.config['ADMINS'], subject='SMTP Failure',
                credentials=auth, secure=secure)
            mail_handler.setLevel(logging.ERROR)
            app.logger.addHandler(mail_handler)

        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/site.log',
                                           maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('Site startup')

    return app


from app import models
