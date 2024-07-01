from flask import Blueprint, render_template, Response, stream_with_context

from app.models import Area, Region, Object, User, LotTradeGOV, CategoryTradeGOV, Parcel, LandParcel, LotTradeGOVRegion, LotTradeGOVAllowedUse
from app.main import main_bp

from flask import request, current_app, url_for, redirect
from flask_login import login_required, current_user
import sqlalchemy as sa

from sqlalchemy import func, text

from app import db, scheduler
from app.cron.tasks import add_additional_lot_info_task_job, add_global_parse_job, add_parse_job

import app.main.parse_additional_data as parse

import csv
from io import StringIO

from time import sleep


# Маршруты
@main_bp.route('/', methods=['GET'])
def index():
    return render_template('home.html')


@main_bp.route('/regions/<int:area_id>')
def regions(area_id):
    area = Area.query.get_or_404(area_id)
    _regions = area.regions.all()
    return render_template('regions.html', area=area, regions=_regions)


@main_bp.route('/objects/<int:region_id>')
def objects(region_id):
    region = Region.query.get_or_404(region_id)
    _objects = region.objects.all()
    return render_template('objects.html', region=region, objects=_objects)


@main_bp.route('/object/<int:object_id>')
def object_detail(object_id):
    _object = Object.query.get_or_404(object_id)
    return render_template('object_detail.html', object=_object)


@main_bp.route('/user/<username>', methods=['GET', 'POST'])
@login_required
def user(username):
    if request.method == 'POST':
        query = request.form.get('action')
        action = int(query.split(';')[0])
        param = int(query.split(';')[1])
        task_is_global = len(query.split(';')) > 2
        if action == -1:
            if param == -1:
                scheduler.remove_job('additional_lot_info_task')
            elif param == 0:
                add_additional_lot_info_task_job(scheduler, db)
            elif param == 1:
                scheduler.pause_job('additional_lot_info_task')
            elif param == 2:
                scheduler.resume_job('additional_lot_info_task')
            else:
                pass
        elif action > 0:
            if param == -1:
                scheduler.remove_job(f'parse_job_{action}{"_global" if task_is_global else ""}')
            elif param == 0:
                if task_is_global:
                    add_global_parse_job(action, scheduler)
                else:
                    add_parse_job(action, scheduler)
            elif param == 1:
                scheduler.pause_job(f'parse_job_{action}{"_global" if task_is_global else ""}')
            elif param == 2:
                scheduler.resume_job(f'parse_job_{action}{"_global" if task_is_global else ""}')
        return redirect(url_for('main.user', username=username))
    else:
        # _user = db.first_or_404(sa.select(User).where(User.username == username))
        if username == current_user.username:
            import pytz
            from datetime import datetime
            tz = pytz.FixedOffset(current_user.user_timezone * 60)  # 3.5 * 60 минут
            # Получаем текущее время в указанном часовом поясе
            now = datetime.now(tz)
            lots_count = LotTradeGOV.query.count()
            lot_categories = CategoryTradeGOV.query.all()
            return render_template('user.html', user=current_user,
                                   lot_categories=lot_categories,
                                   user_time=now, scheduler=scheduler, lots_count=lots_count)
        else:
            return redirect('/')


@main_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def user_settings():
    if request.method == 'POST':
        if 'password' in request.form:
            # Обработка формы изменения пароля
            current_password = request.form['currentPassword']
            new_password = request.form['newPassword']
            confirm_password = request.form['confirmPassword']

            # Здесь можно добавить логику проверки и изменения пароля

        elif 'general' in request.form:
            # Обработка формы общих настроек
            timezone = float(request.form['timezone'])
            about_me = request.form['about']
            email = request.form['email']

            # Обновляем данные пользователя в базе данных
            current_user.user_timezone = timezone
            current_user.about_me = about_me
            current_user.email = email
            db.session.commit()

    return render_template('user/settings.html', user=current_user)


@main_bp.route('/download_csv')
@login_required
def download_csv():
    # Получить общее количество записей в БД
    total_records = LotTradeGOV.query.count()

    # Определить количество записей на странице
    records_per_page = 1000

    column_headers = [column.key for column in LotTradeGOV.__table__.columns]

    # Получить параметры per_file и part из GET-запроса
    per_file = request.args.get('per_file', None)
    part = request.args.get('part', None)

    if per_file:
        per_file = int(per_file)

    if part:
        part = int(part)

        # Функция для удаления переносов строк из текстовых данных
    def remove_newlines(_text):
        return _text.replace('\n', ' ').replace('\r', '').replace('"', "'")

    def generate():
        # Отправить заголовки
        yield ','.join(column_headers) + '\n'

        # Если part не задан, отправляем все записи
        if not part:
            for offset in range(0, total_records, records_per_page):
                lot_data = LotTradeGOV.query.order_by(LotTradeGOV.id).offset(offset).limit(records_per_page).all()
                for row in lot_data:
                    cleaned_row = [f'"{remove_newlines(str(getattr(row, column)))}"' for column in column_headers]
                    yield ','.join(cleaned_row) + '\n'
        # Если part задан, отправляем только часть записей
        else:
            start = (part - 1) * per_file
            end = min(start + per_file, total_records)

            if start < total_records:
                for offset in range(start, end, records_per_page):
                    lot_data = LotTradeGOV.query.order_by(LotTradeGOV.id).offset(offset).limit(records_per_page).all()
                    for row in lot_data:
                        cleaned_row = [f'"{remove_newlines(str(getattr(row, column)))}"' for column in column_headers]
                        yield ','.join(cleaned_row) + '\n'

    # Если параметр part не задан, отправляем данные в одном файле
    if not part:
        response_headers = {'Content-Disposition': 'attachment; filename="lot_data.csv"'}
        return Response(stream_with_context(generate()), headers=response_headers, content_type='text/csv')
    # Если параметр part задан, отправляем часть данных в отдельном файле
    else:
        response_headers = {'Content-Disposition': f'attachment; filename="lot_data_part_{part}.csv"'}
        return Response(stream_with_context(generate()), headers=response_headers, content_type='text/csv')


@main_bp.route('/manage_regions')
@login_required
def manage_regions():
    _regions = LotTradeGOVRegion.query.order_by(LotTradeGOVRegion.id).paginate()
    return render_template('user/manage_regions.html', regions=_regions)


@main_bp.route('/manage_allowed_use')
@login_required
def manage_allowed_use():
    _allowed_use = LotTradeGOVAllowedUse.query.order_by(LotTradeGOVAllowedUse.id).paginate()
    return render_template('user/manage_allowed_use.html', allowed_use=_allowed_use)


@main_bp.route('/manage_subscriptions')
@login_required
def manage_subscriptions():
    return render_template('user/manage_subscriptions.html')
