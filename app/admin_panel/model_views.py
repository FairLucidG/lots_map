from app import admin, db
from flask_admin.form import Select2Widget
from wtforms.fields import SelectField
from flask_admin.contrib.sqla import ModelView
from app.models import User, Area, Region, Object, LotTradeGOV, CategoryTradeGOV, Filter, Subscription, SidebarParameter


# Класс с возможностью экспорта в CSV
class LotTradeGOVModelView(ModelView):
    can_export = True


class UserAdminView(ModelView):
    column_list = ('username', 'email', 'role_name', 'about_me', 'last_seen')  # добавьте 'role_name' в список колонок

    def role_name(self, instance):
        return instance.role_name()

    form_overrides = {
        'role_id': SelectField
    }

    form_args = {
        'role_id': {
            'widget': Select2Widget(),
            'coerce': int
        }
    }


def init_model_views():
    admin.add_views(UserAdminView(User, db.session))
    admin.add_views(ModelView(Area, db.session, category="Ski resort"))
    admin.add_views(ModelView(Region, db.session, category="Ski resort"))
    admin.add_views(ModelView(Object, db.session, category="Ski resort"))
    admin.add_views(LotTradeGOVModelView(LotTradeGOV, db.session, category="Trade GOV"))
    admin.add_views(ModelView(CategoryTradeGOV, db.session, category="Trade GOV"))

    admin.add_views(ModelView(Subscription, db.session))
    admin.add_views(ModelView(Filter, db.session))
    admin.add_views(ModelView(SidebarParameter, db.session))
