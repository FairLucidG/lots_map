import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    # DEBUG = True
    # FLASK_DEBUG = 1

    CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = 'FJxBal14nM66_fEXAJ6YNWA-NcsHAjaM'
    SECRET_KEY = 'K0R0o8FQReJS6P1tgrx4d-4ZqfahGyio'

    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:Lk5Wygyz59@127.0.0.1:5433/map_ne'
    SQLALCHEMY_TRACK_MODIFICATIONS = True

    MAIL_SERVER = 'smtp.server.ru'
    MAIL_PORT = 465
    MAIL_USE_TLS = 1
    MAIL_USERNAME = 'robot@msite.ru'
    MAIL_PASSWORD = ''
    ADMINS = ['support@site.ru']

    SCHEDULER_EXECUTORS = {"default": {"type": "threadpool", "max_workers": 25}}
    # указываем разрешенные хосты
    # SCHEDULER_ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
    # включаем API планировщика
    # SCHEDULER_API_ENABLED = True


class ProductionConfig(Config):
    DEBUG = False


class DevelopConfig(Config):
    DEBUG = True
    ASSETS_DEBUG = True
