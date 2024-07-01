import jwt
from app import db, login, admin
from time import time
from hashlib import md5
from typing import Optional
import sqlalchemy as sa
import sqlalchemy.orm as so
from flask import current_app
from flask_login import UserMixin
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash

import json
from geoalchemy2 import Geometry


# Модели
class Area(db.Model):
    __tablename__ = 'ski_resort_areas'

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.String(100), index=True)
    regions = db.relationship('Region', backref='ski_resort_areas', lazy='dynamic')


class Region(db.Model):
    __tablename__ = 'ski_resort_regions'

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.String(100), index=True)

    area_id = db.Column(db.Integer, db.ForeignKey('ski_resort_areas.id'), nullable=False)
    objects = db.relationship('Object', backref='ski_resort_regions', lazy='dynamic')


class Object(db.Model):
    __tablename__ = 'ski_resort_objects'

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description: so.Mapped[str] = so.mapped_column(sa.String(1000), index=True)
    coords: so.Mapped[str] = so.mapped_column(sa.String(100), index=True)
    symb: so.Mapped[str] = so.mapped_column(sa.String(10), index=True)
    region_id = db.Column(db.Integer, db.ForeignKey('ski_resort_regions.id'), nullable=False)


class SidebarParameter(db.Model):
    __tablename__ = 'sidebar_parameters'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    icon = db.Column(db.String(255), default='', nullable=False)
    db_column_name = db.Column(db.String(100), nullable=False)
    db_table_name = db.Column(db.String(32), default='lots_trade_gov', nullable=False)
    param_type = db.Column(db.String(32), default='text', nullable=False)
    param_unit = db.Column(db.String(16), default='', nullable=False)
    sidebar_index = db.Column(db.Integer, nullable=True)


class Filter(db.Model):
    __tablename__ = 'filters'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    filter_parameter = db.Column(db.String(100), nullable=False)
    db_table_name = db.Column(db.String(32), default='lots_trade_gov', nullable=False)
    parameter_type = db.Column(db.String(20), nullable=False)
    accordion_group = db.Column(db.String(20), nullable=False)
    accordion_group_id = db.Column(db.String(20), default='main_filters', nullable=False)
    accordion_index = db.Column(db.Integer, nullable=True)


class FilterSubscription(db.Model):
    __tablename__ = 'filter_subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    filter_id = db.Column(db.Integer, db.ForeignKey('filters.id'), index=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id'), index=True)

    filter = db.relationship('Filter', backref='filter_subscriptions')
    subscription = db.relationship('Subscription', backref='filter_subscriptions')


class FilterRangeRestriction(db.Model):
    __tablename__ = 'filter_range_restrictions'

    id = db.Column(db.Integer, primary_key=True)
    filter_id = db.Column(db.Integer, db.ForeignKey('filters.id'), index=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id'), index=True)
    min_value = db.Column(db.Float, nullable=True)
    max_value = db.Column(db.Float, nullable=True)
    relative_date = db.Column(db.DateTime, nullable=True)
    allowed_values = db.Column(db.Text, nullable=True)  # For list of allowed values (e.g., "value1,value2,value3")

    filter = db.relationship('Filter', backref='filter_range_restrictions')
    subscription = db.relationship('Subscription', backref='filter_range_restrictions')


class Subscription(db.Model):
    __tablename__ = 'subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, index=True)


# Таблица связи между пользователями и подписками
class UserSubscriptionAssociation(db.Model):
    __tablename__ = 'user_subscription_association'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id'), index=True)
    expired = db.Column(db.DateTime)

    user = db.relationship('User', backref='user_subscription_associations')
    subscription = db.relationship('Subscription', backref='user_subscription_associations')


class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)

    def __repr__(self):
        return '<Role {}>'.format(self.name)


class Priority(db.Model):
    __tablename__ = 'priorities'
    __table_args__ = (
        db.UniqueConstraint('lot_id', 'user_id'),
    )

    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.String(100))
    priority = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    username: so.Mapped[str] = so.mapped_column(sa.String(64), index=True,
                                                unique=True)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True,
                                             unique=True)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))
    about_me: so.Mapped[Optional[str]] = so.mapped_column(sa.String(140))
    last_seen: so.Mapped[Optional[datetime]] = so.mapped_column(
        default=lambda: datetime.now(timezone.utc))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), default=4)  # 4 corresponds to 'Newbie' role ID

    role = db.relationship('Role', backref=db.backref('users', lazy='dynamic'))
    # Таблица связи между пользователями и подписками
    subscriptions = db.relationship('Subscription', secondary='user_subscription_association', backref='users')

    user_timezone: so.Mapped[Optional[float]] = so.mapped_column(sa.Float, default=0)

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def has_role(self, role_name):
        return self.role.name == role_name

    def role_name(self):
        if self.role:
            return self.role.name
        else:
            return "No role assigned"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return f'https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}'

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            current_app.config['SECRET_KEY'], algorithm='HS256')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            _id = jwt.decode(token, current_app.config['SECRET_KEY'],
                             algorithms=['HS256'])['reset_password']
        except Exception:
            return
        return db.session.get(User, _id)


class Parcel(db.Model):
    __tablename__ = 'parcels'
    id = db.Column(db.String(length=128), primary_key=True)
    coordinates = db.Column(Geometry('POINT'))
    polygon = db.Column(Geometry('POLYGON'), nullable=True)

    # lot_trade_gov = db.relationship('LotTradeGOV', backref='parcel', lazy='joined')

    @staticmethod
    def add_parcel(parcel_id, latitude, longitude, polygon_coordinates):
        point = f'POINT({latitude} {longitude})'
        polygon_wkt = 'POLYGON((' + ', '.join([f'{coords[0]} {coords[1]}' for coords in polygon_coordinates]) + '))'
        new_parcel = Parcel(id=parcel_id, coordinates=point, polygon=polygon_wkt)
        db.session.add(new_parcel)
        db.session.commit()

    @staticmethod
    def get_data_as_strings(parcel_id):
        parcel = Parcel.query.filter_by(id=parcel_id).first()
        if parcel:
            coordinates = [parcel.coordinates.x, parcel.coordinates.y]  # json.dumps([parcel.coordinates.x, parcel.coordinates.y])
            polygon_coordinates = [[point.x, point.y] for point in parcel.polygon.exterior.coords]
            # polygon = json.dumps(polygon_coordinates)
            return coordinates, polygon_coordinates
        else:
            return None, None


class LotTradeGOVRegion(db.Model):
    __tablename__ = 'lots_trade_gov_regions'
    id = db.Column(db.Integer, primary_key=True)
    region_code = db.Column(db.Integer, unique=True)
    federal_district = db.Column(db.String(255))
    region_name = db.Column(db.String(255))

    def __repr__(self):
        return f"<Region(region_code='{self.region_code}', federal_district='{self.federal_district}', region_name='{self.region_name}')>"


class LotTradeGOVAllowedUse(db.Model):
    __tablename__ = 'lots_trade_gov_allowed_use'
    id = db.Column(db.Integer, primary_key=True)
    allowed_use = db.Column(db.String(1024), unique=True, nullable=False)
    rubric = db.Column(db.String(256), nullable=False)

    def __repr__(self):
        return f"<AllowedUse id={self.id}, allowed_use='{self.allowed_use}', rubric='{self.rubric}'>"


class LotTradeGOV(db.Model):
    __tablename__ = 'lots_trade_gov'

    id: so.Mapped[str] = so.mapped_column(sa.String(length=128), primary_key=True)
    lot_name: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    lot_status: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    bidd_form: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    notice_number: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    lot_number: so.Mapped[int] = so.mapped_column(sa.Integer, default=0, nullable=True)
    bidd_type: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    subject_rf_code: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    lot_description: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)

    price_min: so.Mapped[float] = so.mapped_column(sa.Float, default=0, nullable=True)
    price_step: so.Mapped[float] = so.mapped_column(sa.Float, default=0, nullable=True)
    currency_code: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)

    etp_code: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    category: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    time_zone_name: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    timezone_offset: so.Mapped[int] = so.mapped_column(sa.Integer, default=0, nullable=True)
    ownership_form: so.Mapped[str] = so.mapped_column(sa.String(length=2048), nullable=True)
    etp_url: so.Mapped[str] = so.mapped_column(sa.String(length=2048), nullable=True)
    deposit: so.Mapped[float] = so.mapped_column(sa.Float, default=0, nullable=True)
    estate_address: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    has_appeals: so.Mapped[bool] = so.mapped_column(sa.Boolean(False), default=False, nullable=True)
    is_stopped: so.Mapped[bool] = so.mapped_column(sa.Boolean(False), default=False, nullable=True)
    auction_start_date: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)

    bidd_start_time: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    bidd_end_time: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)

    version_id: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    is_annulled: so.Mapped[bool] = so.mapped_column(sa.Boolean(False), default=False, nullable=True)
    lot_vat: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    npa_hint_code: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    type_transaction: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)

    permitted_use: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    contract_type: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    cadaster_number: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    area: so.Mapped[float] = so.mapped_column(sa.Float, default=0, nullable=True)
    url: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)

    last_updated: so.Mapped[sa.DateTime] = so.mapped_column(sa.DateTime, default=datetime.now(), nullable=True)
    # final_price: so.Mapped[float] = so.mapped_column(sa.Float, default=0, nullable=True)

    rent_period: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    rent_term: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    auction_step_percent: so.Mapped[float] = so.mapped_column(sa.Float, default=0, nullable=True)

    deposit_percent: so.Mapped[float] = so.mapped_column(sa.Float, default=0, nullable=True)
    recipient: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    recipient_inn: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    deposit_rules: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    deposit_return_rules: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    deposit_electronic_platform: so.Mapped[bool] = so.mapped_column(sa.Boolean(False), default=False, nullable=True)
    deposit_recipient_name: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    deposit_recipient_inn: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    deposit_recipient_kpp: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    deposit_bank_name: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    deposit_bik: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    deposit_pay_account: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    deposit_cor_account: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    deposit_purpose_payment: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)

    protocol_results_participant_price: so.Mapped[float] = so.mapped_column(sa.Float, default=0, nullable=True)
    protocol_results_order_number: so.Mapped[str] = so.mapped_column(sa.String(length=128), default='', nullable=True)
    protocol_results_full_name: so.Mapped[str] = so.mapped_column(sa.String(length=512), default='', nullable=True)
    protocol_results_lastName: so.Mapped[str] = so.mapped_column(sa.String(length=256), default='', nullable=True)
    protocol_results_firstName: so.Mapped[str] = so.mapped_column(sa.String(length=256), default='', nullable=True)
    protocol_results_middleName: so.Mapped[str] = so.mapped_column(sa.String(length=256), default='', nullable=True)
    protocol_results_orgType: so.Mapped[str] = so.mapped_column(sa.String(length=128), default='', nullable=True)
    protocol_results_inn: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    protocol_results_kpp: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)

    reg_number_egrokn: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    participation_fee: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    land_restrictions: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    construction_parameters_max: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    construction_parameters_min: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    connection_etsn: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    deposit_refund: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)
    contract_sign_period: so.Mapped[str] = so.mapped_column(sa.String(length=2048), default='', nullable=True)

    forSmallBusiness: so.Mapped[str] = so.mapped_column(sa.String(length=128), default='', nullable=True)
    coordinates: so.Mapped[str] = so.mapped_column(sa.String(length=64), default='', nullable=True)
    polygon: so.Mapped[str] = so.mapped_column(sa.String(length=8192), default='', nullable=True)
    additional_info: so.Mapped[str] = so.mapped_column(sa.String(length=8192), default='', nullable=True)

    #_parcel_id = db.Column(db.String(128), db.ForeignKey('parcels.id'))
    #_parcel = db.relationship('Parcel', foreign_keys=[_parcel_id])
    #landparcel_id = db.Column(db.String(128), db.ForeignKey('land_parcel.id'))
    #landparcel = db.relationship('LandParcel', foreign_keys=[landparcel_id])


class LandParcel(db.Model):
    __tablename__ = 'land_parcel'
    id = db.Column(db.String(length=128), primary_key=True)
    description = db.Column(db.Text, nullable=True)
    cadastral_number = db.Column(db.String(64), nullable=True)
    address = db.Column(db.String(1024), nullable=True)
    land_category = db.Column(db.String(100), nullable=True)
    purpose = db.Column(db.String(256), nullable=True)
    cadastral_value = db.Column(db.Float, nullable=True)
    cadastral_value_unit = db.Column(db.String(32), nullable=True)
    area = db.Column(db.Float, nullable=True)
    area_unit = db.Column(db.String(20), nullable=True)
    area_type = db.Column(db.String(50), nullable=True)
    ownership_form = db.Column(db.String(512), nullable=True)
    permitted_use = db.Column(db.String(512), nullable=True)
    valuation_date = db.Column(db.Date, nullable=True)
    application_date = db.Column(db.Date, nullable=True)
    data_entry_date = db.Column(db.Date, nullable=True)
    approval_date = db.Column(db.Date, nullable=True)
    land_status = db.Column(db.String(50), nullable=True)

    #lot_trade_gov = db.relationship('LotTradeGOV', backref='land_parcel', lazy='joined')


class LandParcelManager:
    def __init__(self, data, parcel_id):
        self.data = data
        self.parcel_id = parcel_id

    def create_new_parcel(self):
        parcel = LandParcel()
        self.set_parcel_attributes(parcel)
        db.session.add(parcel)
        db.session.commit()

    def update_parcel(self):
        parcel = LandParcel.query.get(self.parcel_id)
        if parcel:
            self.set_parcel_attributes(parcel)
            db.session.commit()

    def select_parcel(self):
        parcel = LandParcel.query.get(self.parcel_id)
        print('OK')
        if parcel:
            parcel_dict = parcel.__dict__
            return {key: value for key, value in parcel_dict.items() if not key.startswith('_')}
        else:
            return None

    def set_parcel_attributes(self, parcel):
        parcel.id = self.parcel_id
        parcel.cadastral_number = self.data.get('id', '')
        parcel.address = self.data.get('address', '')
        parcel.land_category = self.data.get('category_type', '')
        parcel.area = self.data.get('area_value', 0.0)
        parcel.area_unit = self.data.get('area_unit', '')
        parcel.area_type = self.data.get('area_type', '')
        parcel.permitted_use = self.data.get('util_by_doc', '')
        parcel.cadastral_value = self.data.get('cad_cost', 0.0)
        parcel.cadastral_value_unit = self.data.get('cad_unit', '')
        parcel.valuation_date = self.parse_date(self.data.get('date_cost'))
        parcel.application_date = self.parse_date(self.data.get('application_date'))
        parcel.data_entry_date = self.parse_date(self.data.get('cc_date_entering'))
        parcel.approval_date = self.parse_date(self.data.get('cc_date_approval'))
        parcel.land_status = self.data.get('statecd', '')

    def parse_date(self, date_str):
        if date_str:
            try:
                return datetime.strptime(date_str, '%d.%m.%Y').date()
            except ValueError:
                pass
        return None


class CategoryTradeGOV(db.Model):
    __tablename__ = 'categories_trade_gov'

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    cat_name: so.Mapped[str] = so.mapped_column(sa.String(length=128))
    cat_id: so.Mapped[str] = so.mapped_column(sa.String(16), unique=True)
    # isNeedParse: so.Mapped[bool] = so.mapped_column(sa.Boolean(True), default=True)


@login.user_loader
def load_user(_id):
    return db.session.get(User, int(_id))
