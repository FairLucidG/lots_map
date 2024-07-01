import os
import pickle
from flask import Blueprint, jsonify, request
from flask_paginate import Pagination, get_page_args
from app.api.generators.filter import *
from flask_login import login_required, current_user
from app.api import api_bp
from app.models import LandParcelManager, LotTradeGOV, SidebarParameter, Filter, Parcel, LotTradeGOVRegion, \
    LotTradeGOVAllowedUse, Priority, FilterSubscription, FilterRangeRestriction, Subscription
import datetime
from datetime import timedelta
from app import db
from sqlalchemy import text, func, asc
import pandas as pd


# Define a custom function to serialize datetime objects
def serialize_datetime(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    raise TypeError("Type not serializable")


@api_bp.route('/api/get_lot_attr/<int:lot_id_p1>_<int:lot_id_p2>')
def get_lot_attr(lot_id_p1, lot_id_p2):
    # _lot = LandParcelManager("", f'{str(lot_id_p1)}_{str(lot_id_p2)}')

    _data = LotTradeGOV.query.get(f'{str(lot_id_p1)}_{str(lot_id_p2)}')

    _sidebar_params = SidebarParameter.query.order_by(asc(SidebarParameter.sidebar_index)).all()

    def create_dict(data_info):
        if data_info:
            parcel_dict = data_info.__dict__
            return {key: value for key, value in parcel_dict.items() if not key.startswith('_')}
        else:
            return None

    def create_dict_list(data_list):
        _result = []
        for _ in data_list:
            _result.append(create_dict(_))
        return _result

    _data = create_dict(_data)
    _sidebar_params = create_dict_list(_sidebar_params)

    print(_data)
    print(_sidebar_params)

    _sorted_data = []
    for param in _sidebar_params:
        if param['param_type'] == 'text':
            if _data[param['db_column_name']] is not None and _data[param['db_column_name']] != "":
                _sorted_data.append({'param': param['name'], 'value': param['icon'] + str(_data[param['db_column_name']]) +
                                                                      (f" {param['param_unit']}" if param[
                                                                          'param_unit'] else '')})
        elif param['param_type'] == 'text_from_list':
            if _data[param['db_column_name']] is not None and _data[param['db_column_name']] != "":
                _sorted_data.append({'param': param['name'],
                                     'value': param['icon'] + associations_list.associations[param['db_column_name']]
                                     [_data[param['db_column_name']]]})
        elif param['param_type'] == 'link':
            if _data[param['db_column_name']] is not None and _data[param['db_column_name']] != "":
                _sorted_data.append({'param': param['name'],
                                     'value': f"""{param['icon']}
                 <a href='{_data[param['db_column_name']]}' target='_blank' title='Открыть страницу лота в новом окне'>
                    {_data[param['db_column_name']]}
                 </a>"""})
        elif param['param_type'] == 'priority':
            if current_user.is_authenticated:
                priority = Priority.query.filter_by(lot_id=_data['id'], user_id=current_user.id).value(db.column('priority')) or 0
                _sorted_data.append({'param': param['name'],
                                     'value': f"""{param['icon']}
                            <label for="priority_slider">
                                <div>
                                    <span class="fw-bold mb-2">{param['name']}: 
                                    <span id="priority_value" class="fw-normal"> {priority}</span></span>
                                </div>
                            </label>
                                 <div id='priority_slider' data='{_data['id']}'></div>
                                 """, 'script': f"""
                                    function init_priority_slider(){{
                                                                            
                                        var priority_value = document.getElementById('priority_value');
                                        var priority_slider = document.getElementById('priority_slider');
                                        
                                        noUiSlider.create(priority_slider, {{
                                            start: [{priority}],
                                            step: 1,
                                            tooltips: [false],
                                            range: {{
                                              'min': 0,
                                              'max': 10
                                            }}
                                        }});
                                        
                                        priority_slider.noUiSlider.set([{priority}], true, true);
                                        
                                        priority_slider.noUiSlider.on('update', function (values, handle) {{
                                            var lotId = priority_slider.getAttribute('data');
                                            var priority = values[0];
                                        
                                            fetch('/api/update_priority', {{
                                                method: 'POST',
                                                headers: {{
                                                    'Content-Type': 'application/x-www-form-urlencoded'
                                                }},
                                                body: 'lot_id=' + encodeURIComponent(lotId) + '&priority=' + encodeURIComponent(priority)
                                            }})
                                            .then(function(response) {{
                                                if (response.ok) {{        
                                                    return response.json();
                                                }} else {{
                                                    throw new Error('Error updating priority: ' + response.statusText);
                                                }}
                                           }})
                                           .then(function(data) {{
                                                if (data.status === 'success') {{
                                                    priority_value.innerText = data.data; // Выводим значение data из ответа
                                                }} else {{
                                                    console.error('Error updating priority:', data.status);
                                                }}
                                            }})
                                            .catch(function(error) {{
                                                console.error('Error updating priority:', error);
                                            }});

                                        }});
                                                                                
                                    }}
                                    
                                    init_priority_slider();
                                 """})

    print(_sorted_data)

    if _data:
        result = {'status': 'success', 'data': _sorted_data}
    else:
        result = {'status': 'error'}

    return jsonify(result)


@api_bp.route('/api/update_priority', methods=['POST'])
@login_required
def update_priority():
    try:
        lot_id = request.form.get('lot_id')
        priority = int(float(request.form.get('priority')))
        user_id = current_user.id

        existing_priority = Priority.query.filter_by(lot_id=lot_id, user_id=user_id).first()

        if existing_priority:
            existing_priority.priority = priority
        else:
            new_priority = Priority(lot_id=lot_id, priority=priority, user_id=user_id)
            db.session.add(new_priority)

        db.session.commit()

        return jsonify({'status': 'success', 'data': priority})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'status': 'error'})


@api_bp.route('/api/get_subscriptions', methods=['GET'])
def get_subscriptions():
    subscriptions = Subscription.query.all()
    result = [{'id': sub.id, 'name': sub.name} for sub in subscriptions]
    return jsonify(result)


@api_bp.route('/api/add_subscription', methods=['POST'])
def add_subscription():
    name = request.form.get('name')
    if name:
        subscription = Subscription(name=name)
        db.session.add(subscription)
        db.session.commit()
        return jsonify({'status': 'success'}), 201
    return jsonify({'status': 'error', 'message': 'Invalid data'}), 400


@api_bp.route('/api/edit_subscription', methods=['POST'])
def edit_subscription():
    id = request.form.get('id')
    name = request.form.get('name')
    subscription = Subscription.query.get(id)
    if subscription and name:
        subscription.name = name
        db.session.commit()
        return jsonify({'status': 'success'}), 200
    return jsonify({'status': 'error', 'message': 'Invalid data or subscription not found'}), 400


@api_bp.route('/api/delete_subscription/<int:id>', methods=['DELETE'])
def delete_subscription(id):
    subscription = Subscription.query.get(id)
    if subscription:
        db.session.delete(subscription)
        db.session.commit()
        return jsonify({'status': 'success'}), 200
    return jsonify({'status': 'error', 'message': 'Subscription not found'}), 404


@api_bp.route('/api/get_filters_data', methods=['GET'])
def get_filters_data():
    filters = Filter.query.all()
    result = [{'id': f.id, 'name': f.name, 'filter_parameter': f.filter_parameter, 'parameter_type': f.parameter_type, 'db_table_name': f.db_table_name} for f in filters]
    return jsonify(result)


@api_bp.route('/api/add_filter', methods=['POST'])
def add_filter():
    name = request.form.get('name')
    filter_parameter = request.form.get('filter_parameter')
    parameter_type = request.form.get('parameter_type')
    db_table_name = request.form.get('db_table_name')
    if name and filter_parameter and parameter_type and db_table_name:
        filter = Filter(name=name, filter_parameter=filter_parameter, parameter_type=parameter_type, db_table_name=db_table_name)
        db.session.add(filter)
        db.session.commit()
        return jsonify({'status': 'success'}), 201
    return jsonify({'status': 'error', 'message': 'Invalid data'}), 400


@api_bp.route('/api/edit_filter', methods=['POST'])
def edit_filter():
    id = request.form.get('id')
    name = request.form.get('name')
    filter_parameter = request.form.get('filter_parameter')
    parameter_type = request.form.get('parameter_type')
    db_table_name = request.form.get('db_table_name')
    filter = Filter.query.get(id)
    if filter and name and filter_parameter and parameter_type and db_table_name:
        filter.name = name
        filter.filter_parameter = filter_parameter
        filter.parameter_type = parameter_type
        filter.db_table_name = db_table_name
        db.session.commit()
        return jsonify({'status': 'success'}), 200
    return jsonify({'status': 'error', 'message': 'Invalid data or filter not found'}), 400


@api_bp.route('/api/delete_filter/<int:id>', methods=['DELETE'])
def delete_filter(id):
    filter = Filter.query.get(id)
    if filter:
        db.session.delete(filter)
        db.session.commit()
        return jsonify({'status': 'success'}), 200
    return jsonify({'status': 'error', 'message': 'Filter not found'}), 404


@api_bp.route('/api/get_filter_ranges', methods=['GET'])
def get_filter_ranges():
    filter_ranges = FilterRangeRestriction.query.all()
    result = [{'id': fr.id, 'filter_id': fr.filter_id, 'subscription_id': fr.subscription_id, 'filter_name': fr.filter.name, 'subscription_name': fr.subscription.name, 'min_value': fr.min_value, 'max_value': fr.max_value, 'relative_date': fr.relative_date, 'allowed_values': fr.allowed_values} for fr in filter_ranges]
    return jsonify(result)


@api_bp.route('/api/add_filter_range', methods=['POST'])
def add_filter_range():
    filter_id = request.form.get('filter_id')
    subscription_id = request.form.get('subscription_id')
    min_value = request.form.get('min_value', 0.0)
    if min_value == '':
        min_value = 0.0
    max_value = request.form.get('max_value', 0.0)
    if max_value == '':
        max_value = 0.0
    relative_date = request.form.get('relative_date', '2075-01-01')
    if relative_date == '':
        relative_date = '2075-01-01'
    allowed_values = request.form.get('allowed_values', '')
    if filter_id and subscription_id:
        filter_range = FilterRangeRestriction(filter_id=filter_id, subscription_id=subscription_id, min_value=min_value, max_value=max_value, relative_date=relative_date, allowed_values=allowed_values)
        db.session.add(filter_range)
        db.session.commit()
        return jsonify({'status': 'success'}), 201
    return jsonify({'status': 'error', 'message': 'Invalid data'}), 400


@api_bp.route('/api/edit_filter_range', methods=['POST'])
def edit_filter_range():
    id = request.form.get('id')
    filter_id = request.form.get('filter_id')
    subscription_id = request.form.get('subscription_id')
    min_value = request.form.get('min_value')
    max_value = request.form.get('max_value')
    relative_date = request.form.get('relative_date')
    allowed_values = request.form.get('allowed_values')
    filter_range = FilterRangeRestriction.query.get(id)
    if filter_range and filter_id and subscription_id:
        filter_range.filter_id = filter_id
        filter_range.subscription_id = subscription_id
        filter_range.min_value = min_value
        filter_range.max_value = max_value
        filter_range.relative_date = relative_date
        filter_range.allowed_values = allowed_values
        db.session.commit()
        return jsonify({'status': 'success'}), 200
    return jsonify({'status': 'error', 'message': 'Invalid data or filter range not found'}), 400


@api_bp.route('/api/delete_filter_range/<int:id>', methods=['DELETE'])
def delete_filter_range(id):
    filter_range = FilterRangeRestriction.query.get(id)
    if filter_range:
        db.session.delete(filter_range)
        db.session.commit()
        return jsonify({'status': 'success'}), 200
    return jsonify({'status': 'error', 'message': 'Filter range not found'}), 404


@api_bp.route('/api/get_combo_box_options/<int:filter_id>', methods=['GET'])
def get_combo_box_options(filter_id):
    filter = Filter.query.get(filter_id)
    if filter:
        if filter.parameter_type == 'combo_box':
            options = db.session.query(getattr(LotTradeGOV, filter.filter_parameter)).distinct().all()
        elif filter.parameter_type == 'combo_box_from_list':
            options = filter.filter_list.split(',') if filter.filter_list else []
        else:
            options = []
        return jsonify([option[0] for option in options])
    return jsonify([]), 404


@api_bp.route('/api/get_filters')
def get_filters():
    user_subscription_ids = [sub.subscription_id for sub in
                             current_user.user_subscription_associations] if current_user.is_authenticated else [
        1]  # Assuming 1 is the ID for the basic subscription

    print('user_subscription_ids', user_subscription_ids)

    filters = Filter.query.join(FilterSubscription).filter(
        FilterSubscription.subscription_id.in_(user_subscription_ids)).order_by(Filter.accordion_group_id,
                                                                                asc(Filter.accordion_index)).all()
    accordions = {}

    print(filters)

    for _filter in filters:
        if _filter.accordion_group not in accordions:
            accordions[_filter.accordion_group] = {'filters': [], 'accordion_group_id': _filter.accordion_group_id}

        range_restriction = FilterRangeRestriction.query.filter_by(filter_id=_filter.id,
                                                                   subscription_id=user_subscription_ids[0]).first()

        if _filter.parameter_type == 'text':
            html = generate_text_filter_html(_filter)

        elif _filter.parameter_type in ['combo_box', 'combo_box_from_list']:
            if _filter.db_table_name == 'lots_trade_gov':
                options = get_cached_filters(_filter.filter_parameter,
                                             lambda: [getattr(res, _filter.filter_parameter) for res in
                                                      LotTradeGOV.query.filter(
                                                          text(f"{_filter.filter_parameter} IS NOT NULL"),
                                                          text(f"{_filter.filter_parameter} != ''")).distinct(
                                                          text(_filter.filter_parameter)).all()])

                if range_restriction and range_restriction.allowed_values:
                    allowed_values = range_restriction.allowed_values.split(',')
                    options = [opt for opt in options if opt in allowed_values]

                html = generate_combo_box_filter_html(_filter, options)

        elif _filter.parameter_type == 'boolean':
            html = generate_boolean_filter_html(_filter)

        elif _filter.parameter_type == 'date_range':
            html = generate_date_range_filter_html(_filter)

        elif _filter.parameter_type == 'double_slider':
            if _filter.db_table_name == 'lots_trade_gov':
                min_value, max_value = get_cached_filters(_filter.filter_parameter, lambda: [
                    db.session.query(db.func.min(LotTradeGOV.__table__.columns[_filter.filter_parameter])).scalar(),
                    db.session.query(db.func.max(LotTradeGOV.__table__.columns[_filter.filter_parameter])).scalar()
                ])

                if range_restriction:
                    if range_restriction.min_value is not None:
                        min_value = max(min_value, range_restriction.min_value)
                    if range_restriction.max_value is not None:
                        max_value = min(max_value, range_restriction.max_value)

                if min_value is not None and max_value is not None:
                    html = generate_double_slider_filter_html(_filter, min_value, max_value)

        print(html)

        accordions[_filter.accordion_group]['filters'].append({'html': html})

    html_output = ""
    for accordion in accordions:
        if accordions[accordion]['filters']:
            html_output += f"""
            <div class="accordion-item">
                <div class="accordion-header" id="heading_{accordions[accordion]['accordion_group_id']}">
                  <button class="accordion-button" type="button" data-bs-toggle="collapse" data-bs-target="#{accordions[accordion]['accordion_group_id']}" aria-expanded="{'true' if accordions[accordion]['accordion_group_id'] == 'main_filters' else 'false'}" aria-controls="{accordions[accordion]['accordion_group_id']}">
                    {accordion}
                  </button>
                </div>
                <div id="{accordions[accordion]['accordion_group_id']}" class="accordion-collapse collapse {'show' if accordions[accordion]['accordion_group_id'] == 'main_filters' else ''}" aria-labelledby="heading_{accordions[accordion]['accordion_group_id']}" data-bs-parent="#filters">
                <div class="row">
                """
            for _filter in accordions[accordion]['filters']:
                html_output += _filter['html']
            html_output += """
                </div>
            </div>
          </div>
        """

    if html_output:
        result = {'status': 'success', 'data': html_output}
    else:
        result = {'status': 'error'}

    return jsonify(result)
'''def get_filters():

    CACHE_DIR = os.path.join(os.getcwd(), 'cache')
    os.makedirs(CACHE_DIR, exist_ok=True)

    filters = Filter.query.order_by(Filter.accordion_group_id, asc(Filter.accordion_index)).all()

    _accordions = {}
    for _filter in filters:

        if _filter.accordion_group not in _accordions:
            _accordions[_filter.accordion_group] = {'filters': [], 'accordion_group_id': _filter.accordion_group_id}

        if _filter.parameter_type == 'text':
            _accordions[_filter.accordion_group]['filters'].append({'html': f"""
                <div class="form-group col-12 col-md-4 mt-2 mb-2">
                    <label for="{_filter.filter_parameter}"><h5>{_filter.name}:</h5></label>
                    <input type="text" class="form-control" id="{_filter.filter_parameter}" name="{_filter.filter_parameter}" value="">
                </div>
            """})

        elif _filter.parameter_type == 'combo_box' or _filter.parameter_type == 'combo_box_from_list':
            if _filter.db_table_name == 'lots_trade_gov':

                def get_combo_box_filters(_filter):

                    cache_file = os.path.join(CACHE_DIR, f"{_filter.filter_parameter}.pickle")

                    _unique_values_list = []

                    if os.path.exists(cache_file):
                        last_modified = datetime.datetime.fromtimestamp(os.path.getmtime(cache_file))
                        if last_modified > datetime.datetime.utcnow() - timedelta(minutes=15):
                            # Загружаем фильтры из кэша
                            with open(cache_file, 'rb') as f:
                                _unique_values_list = pickle.load(f)
                        else:
                            # Генерируем фильтры из базы данных
                            _unique_values = LotTradeGOV.query. \
                                filter(text(f"{_filter.filter_parameter} IS NOT NULL"),
                                       text(f"{_filter.filter_parameter} != ''")). \
                                distinct(text(_filter.filter_parameter)).all()
                            _unique_values_list = [getattr(_result, _filter.filter_parameter) for _result in
                                                   _unique_values]

                            # Сохраняем фильтры в кэш
                            with open(cache_file, 'wb') as f:
                                pickle.dump(_unique_values_list, f)
                    else:
                        # Генерируем фильтры из базы данных
                        _unique_values = LotTradeGOV.query. \
                            filter(text(f"{_filter.filter_parameter} IS NOT NULL"),
                                   text(f"{_filter.filter_parameter} != ''")). \
                            distinct(text(_filter.filter_parameter)).all()
                        _unique_values_list = [getattr(_result, _filter.filter_parameter) for _result in _unique_values]

                        # Сохраняем фильтры в кэш
                        with open(cache_file, 'wb') as f:
                            pickle.dump(_unique_values_list, f)

                    return _unique_values_list

                unique_values_list = get_combo_box_filters(_filter)
                if unique_values_list:
                    temp_html = f"""<div class="form-group col-12 col-md-4 mt-2 mb-2">
                            <label for="{_filter.filter_parameter}"><h5>{_filter.name}:</h5></label>
                            <select class="form-control" id="{_filter.filter_parameter}" name="{_filter.filter_parameter}">
                    """
                    temp_html += f"<option value='none'>--- Не задано ---</option>"
                    for value in unique_values_list:
                        if _filter.parameter_type == 'combo_box':
                            temp_html += f"<option>{value}</option>"
                        else:
                            # print(f'param: {_filter.filter_parameter} | val: {value}')
                            assoc_value = associations_list.associations[_filter.filter_parameter][value]
                            temp_html += f"<option value='{value}'>{assoc_value}</option>"
                    temp_html += '</select></div>'
                    _accordions[_filter.accordion_group]['filters'].append({'html': temp_html})

        elif _filter.parameter_type == 'boolean':
            temp_html = f"""<div class="form-group col-12 col-md-4 mt-2 mb-2">
                                        <label for="{_filter.filter_parameter}"><h5>{_filter.name}:</h5></label>
                                        <select class="form-control" id="{_filter.filter_parameter}" name="{_filter.filter_parameter}">
                                """
            temp_html += f"<option value='none'>--- Не задано ---</option>"
            temp_html += f"<option value='yes'>Да</option>"
            temp_html += f"<option value='no'>Нет</option>"
            temp_html += '</select></div>'
            _accordions[_filter.accordion_group]['filters'].append({'html': temp_html})

        elif _filter.parameter_type == 'date_range':
            temp_html = f"""<div class="form-group col-12 col-md-4 mt-2 mb-2">
                                    <label for="{_filter.filter_parameter}_min"><h5>{_filter.name} (от):</h5></label>
                                    <input type="date" id="{_filter.filter_parameter}_min" class="form-control"></input>
                                </div>"""
            temp_html += f"""<div class="form-group col-12 col-md-4 mt-2 mb-2">
                                    <label for="{_filter.filter_parameter}_max"><h5>{_filter.name} (до):</h5></label>
                                    <input type="date" id="{_filter.filter_parameter}_max" class="form-control"></input>
                                </div>"""
            temp_html += f"""
                <input type="hidden" id="{_filter.filter_parameter}" name="{_filter.filter_parameter}">
            """
            temp_html += f"""
                <script>
                    var {_filter.filter_parameter} = document.getElementById('{_filter.filter_parameter}');
                    var {_filter.filter_parameter}_min = document.getElementById('{_filter.filter_parameter}_min');
                    var {_filter.filter_parameter}_max = document.getElementById('{_filter.filter_parameter}_max');
                    
                    {_filter.filter_parameter}_min.addEventListener('input', function () {{
                        var min_value = {_filter.filter_parameter}_min.value;
                        var max_value = {_filter.filter_parameter}_max.value;
                        {_filter.filter_parameter}.value = min_value + '|' + max_value;
                    }});
                    
                    {_filter.filter_parameter}_max.addEventListener('input', function () {{
                        var min_value = {_filter.filter_parameter}_min.value;
                        var max_value = {_filter.filter_parameter}_max.value;
                        {_filter.filter_parameter}.value = min_value + '|' + max_value;
                    }});
                </script>
            """
            _accordions[_filter.accordion_group]['filters'].append({'html': temp_html})

        elif _filter.parameter_type == 'double_slider':
            if _filter.db_table_name == 'lots_trade_gov':

                def get_min_max_filters(_filter):

                    cache_file_min = os.path.join(CACHE_DIR, f"{_filter.filter_parameter}_min.pickle")
                    cache_file_max = os.path.join(CACHE_DIR, f"{_filter.filter_parameter}_max.pickle")

                    _min_value, _max_value = None, None

                    if os.path.exists(cache_file_min):
                        last_modified = datetime.datetime.fromtimestamp(os.path.getmtime(cache_file_min))
                        if last_modified > datetime.datetime.utcnow() - timedelta(minutes=15):
                            # Загружаем фильтры из кэша
                            with open(cache_file_min, 'rb') as f:
                                _min_value = pickle.load(f)
                            with open(cache_file_max, 'rb') as f:
                                _max_value = pickle.load(f)
                        else:
                            # Генерируем фильтры из базы данных
                            _min_value = db.session.query(
                                db.func.min(LotTradeGOV.__table__.columns[_filter.filter_parameter])
                            ).scalar()
                            _max_value = db.session.query(
                                db.func.max(LotTradeGOV.__table__.columns[_filter.filter_parameter])
                            ).scalar()

                            # Сохраняем фильтры в кэш
                            with open(cache_file_min, 'wb') as f:
                                pickle.dump(_min_value, f)
                            with open(cache_file_max, 'wb') as f:
                                pickle.dump(_max_value, f)
                    else:
                        # Генерируем фильтры из базы данных
                        _min_value = db.session.query(
                            db.func.min(LotTradeGOV.__table__.columns[_filter.filter_parameter])
                        ).scalar()
                        _max_value = db.session.query(
                            db.func.max(LotTradeGOV.__table__.columns[_filter.filter_parameter])
                        ).scalar()

                        # Сохраняем фильтры в кэш
                        with open(cache_file_min, 'wb') as f:
                            pickle.dump(_min_value, f)
                        with open(cache_file_max, 'wb') as f:
                            pickle.dump(_max_value, f)

                    return _min_value, _max_value

                min_value, max_value = get_min_max_filters(_filter)

                if isinstance(min_value, (int, float)) and isinstance(max_value, (int, float)):
                    temp_html = f"""
                        <div class="form-group col-12 col-md-4 mt-2 mb-2">
                            <label for="{_filter.filter_parameter}">
                                <div>
                                    <span class="fw-bold">{_filter.name}:</span>
                                    <div>
                                        От <input type="number" id="{_filter.filter_parameter}_value_min" step="0.01" value="{min_value}"></input> 
                                        До <input type="number" id="{_filter.filter_parameter}_value_max" step="0.01" value="{max_value}"></input>
                                    </div>
                                </div>
                            </label>                            
                            <input type="hidden" id="{_filter.filter_parameter}_hidden" name="{_filter.filter_parameter}">
                            <div id="{_filter.filter_parameter}"></div>
                            <script>
                                var {_filter.filter_parameter} = document.getElementById('{_filter.filter_parameter}');                                
                                var {_filter.filter_parameter}_value_min = document.getElementById('{_filter.filter_parameter}_value_min');
                                var {_filter.filter_parameter}_value_max = document.getElementById('{_filter.filter_parameter}_value_max');
                                var {_filter.filter_parameter}_hidden = document.getElementById('{_filter.filter_parameter}_hidden');
                                
                                noUiSlider.create({_filter.filter_parameter}, {{
                                    start: [{min_value}, {max_value}],
                                    tooltips: [false, false],
                                    range: {{
                                      'min': {min_value},
                                      'max': {max_value}
                                    }}
                                }});
                                
                                {_filter.filter_parameter}.noUiSlider.on('update', function (values, handle) {{
                                    {_filter.filter_parameter}_value_min.value = values[0];
                                    {_filter.filter_parameter}_value_max.value = values[1];
                                    {_filter.filter_parameter}_hidden.value = values[0] + '|' + values[1];
                                }});
                                
                                {_filter.filter_parameter}_value_min.addEventListener('input', function () {{
                                    var min_value = parseFloat(this.value);
                                    var max_value = parseFloat({_filter.filter_parameter}_value_max.value);
                                    if (min_value > max_value) {{
                                        min_value = max_value;
                                    }}
                                    {_filter.filter_parameter}.noUiSlider.set([min_value, max_value], true, true);
                                }});
                                
                                {_filter.filter_parameter}_value_max.addEventListener('input', function () {{
                                    var min_value = parseFloat({_filter.filter_parameter}_value_min.value);
                                    var max_value = parseFloat(this.value);
                                    if (max_value < min_value) {{
                                        max_value = min_value;
                                    }}
                                    {_filter.filter_parameter}.noUiSlider.set([min_value, max_value], true, true);
                                }});
                            </script>
                        </div>
                    """
                    _accordions[_filter.accordion_group]['filters'].append({'html': temp_html})

    html = ""

    for _accordion in _accordions:
        if _accordions[_accordion]['filters']:
            html += f"""
                <div class="accordion-item">
                    <div class="accordion-header" id="heading_{_accordions[_accordion]['accordion_group_id']}">
                      <button class="accordion-button" type="button" data-bs-toggle="collapse" data-bs-target="#{_accordions[_accordion]['accordion_group_id']}" aria-expanded="{'true' if _accordions[_accordion]['accordion_group_id'] == 'main_filters' else 'false'}" aria-controls="{_accordions[_accordion]['accordion_group_id']}">
                        {_accordion}
                      </button>
                    </div>
                    <div id="{_accordions[_accordion]['accordion_group_id']}" class="accordion-collapse collapse {'show' if _accordions[_accordion]['accordion_group_id'] == 'main_filters' else ''}" aria-labelledby="heading_{_accordions[_accordion]['accordion_group_id']}" data-bs-parent="#filters">
                    <div class="row">
            """
            for _filter in _accordions[_accordion]['filters']:
                html += _filter['html']
            html += """
                    </div>
                </div>
              </div>
            """

    if html:
        result = {'status': 'success', 'data': html}
    else:
        result = {'status': 'error'}

    # return json.dumps(result, ensure_ascii=True, indent=4, sort_keys=True, default=str).encode('utf8')
    return jsonify(result)'''


@api_bp.route('/api/get_lots_by_filters', methods=['POST'])
def get_lots_by_filters():
    data = request.form
    zoom = request.args.get('zoom', 4, type=int)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    return_table = request.args.get('table', 'false').lower() == 'true'

    clusters = None

    print('Table:', return_table)

    bounds = request.args.get('bounds', '1, 1, 1, 1')
    center_point = request.args.get('center', '99.505405,61.698652999991054')

    # Извлекаем координаты юго-западной и северо-восточной точек из bounds
    try:
        sw_lng, sw_lat, ne_lng, ne_lat = bounds.split(',')
    except:
        sw_lng, sw_lat, ne_lng, ne_lat = 1, 1, 1, 1

    try:
        center_lat, center_lng = center_point.split(',')
    except:
        center_lat, center_lng = 99.505405, 61.698652999991054

    # Создаем геометрию прямоугольника на основе границ
    # envelope = func.ST_MakeEnvelope(sw_lng, sw_lat, ne_lng, ne_lat)
    center_point = func.ST_MakePoint(float(center_lat), float(center_lng))

    if data:

        filters = Filter.query.all()

        lot_trade_gov_query = LotTradeGOV.query.with_entities(LotTradeGOV.id)

        for value in data:
            if data[value] == 'none' or data[value] == '':
                continue
            for _filter in filters:
                if _filter.filter_parameter != value:
                    continue
                if _filter.parameter_type == 'text' or _filter.parameter_type == 'combo_box' or _filter.parameter_type == 'combo_box_from_list':
                    lot_trade_gov_query = lot_trade_gov_query.filter(
                        text(f"{_filter.filter_parameter} = '{data[value]}'"))
                elif _filter.parameter_type == 'boolean':
                    lot_trade_gov_query = lot_trade_gov_query.filter(
                        text(f"{_filter.filter_parameter} = {'True' if data[value] == 'true' else 'False'}"))
                elif _filter.parameter_type == 'date_range':
                    min_value, max_value = data[value].split('|')
                    if min_value:
                        lot_trade_gov_query = lot_trade_gov_query.filter(
                            text(f"{_filter.filter_parameter} >= '{min_value}'"))
                    if max_value:
                        lot_trade_gov_query = lot_trade_gov_query.filter(
                            text(f"{_filter.filter_parameter} <= '{max_value}'"))
                elif _filter.parameter_type == 'double_slider':
                    min_value, max_value = data[value].split('|')
                    lot_trade_gov_query = lot_trade_gov_query.filter(
                        text(f"{_filter.filter_parameter} >= '{min_value}'"),
                        text(f"{_filter.filter_parameter} <= '{max_value}'"))

        if return_table:
            lot_trade_gov_query = LotTradeGOV.query.with_entities(LotTradeGOV.id, LotTradeGOV.lot_name)
            print('get table')
            offset = (page - 1) * per_page
            lots = lot_trade_gov_query.offset(offset).limit(per_page).all()
            total = lot_trade_gov_query.count()

            table_data = [{'param': lot.id, 'value': lot.lot_name} for lot in lots]
            print(table_data)

            pagination = Pagination(page=page, per_page=per_page, total=total, css_framework='bootstrap4')
            return jsonify({
                'table_data': table_data,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': pagination.pages
                }
            })
        else:
            results = lot_trade_gov_query.all()

            lot_ids = [result.id for result in results] if results else []
            _objects = Parcel.query.with_entities(
                Parcel.id,
                func.ST_X(Parcel.coordinates).label('x'),
                func.ST_Y(Parcel.coordinates).label('y')
            ).filter(Parcel.id.in_(lot_ids)).all() if lot_ids else []

    else:
        if return_table:
            lot_trade_gov_query = LotTradeGOV.query.with_entities(LotTradeGOV.id, LotTradeGOV.lot_name)
            print('get table')
            offset = (page - 1) * per_page
            lots = lot_trade_gov_query.offset(offset).limit(per_page).all()
            total = lot_trade_gov_query.count()

            table_data = [{'param': lot.id, 'value': lot.lot_name} for lot in lots]
            print(table_data)

            pagination = Pagination(page=page, per_page=per_page, total=total, css_framework='bootstrap4')
            return jsonify({
                'table_data': table_data,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': pagination.pages
                }
            })
        else:
            '''_objects = Parcel.query.with_entities(
                Parcel.id,
                func.ST_X(Parcel.coordinates).label('x'),
                func.ST_Y(Parcel.coordinates).label('y')
            ).all()'''
            print('get map')
            zoom_coefficient = 2 ** (zoom - 4)
            radius = 400000 / zoom_coefficient * 10
            # zoom = 4
            # Определяем размер сетки в зависимости от zoom
            grid_size = 0.00085 * (2 ** (18 - zoom))
            # distance_threshold = 0.0002 * (2 ** (18 - zoom))

            from geoalchemy2 import Geography

            with db.session.no_autoflush:
                distance_cte = db.session.query(
                    Parcel.id,
                    Parcel.coordinates,
                    func.ROUND(func.ST_DISTANCE(Parcel.coordinates.cast(Geography), center_point.cast(Geography)) / 1000).label('dist')
                ).where(
                    func.ST_DISTANCE(Parcel.coordinates.cast(Geography), center_point.cast(Geography)) < radius
                ).cte('distance_cte')

                '''results = db.session.query(
                    func.ROUND(distance_cte.c.dist).label('distance_group'),
                    func.string_agg(func.concat(func.ST_X(distance_cte.c.coordinates), ',', func.ST_Y(distance_cte.c.coordinates)), ', ').label('coordinates'),
                    func.count(distance_cte.c.id).label('count')
                ).group_by(
                    func.ROUND(distance_cte.c.dist)
                ).order_by(
                    'distance_group'
                ).all()'''

                results = db.session.query(
                    # func.ROUND(distance_cte.c.dist).label('distance_group'),
                    func.ST_X(func.ST_Centroid(func.ST_Collect(distance_cte.c.coordinates))).label('x'),
                    func.ST_Y(func.ST_Centroid(func.ST_Collect(distance_cte.c.coordinates))).label('y'),
                    func.count(distance_cte.c.id).label('count')
                ).group_by(
                    # func.ROUND(distance_cte.c.dist),
                    func.ST_SnapToGrid(distance_cte.c.coordinates, grid_size)
                ).order_by(
                    'x'  # 'distance_group'
                ).all()

            # print(results)

            clusters = [{'x': result.x, 'y': result.y, 'count': result.count} for result in results]

            '''clusters = [{'distance': result.distance_group, 'coordinates': result.coordinates, 'count': result.count}
                        for result in results]'''

            # Выполняем кластеризацию с использованием функции ST_SnapToGrid
            '''results = db.session.query(
                func.ST_X(func.ST_Centroid(func.ST_Collect(Parcel.coordinates))).label('x'),
                func.ST_Y(func.ST_Centroid(func.ST_Collect(Parcel.coordinates))).label('y'),
                func.count(Parcel.id).label('count')
            ).filter(
                func.ST_DWithin(Parcel.coordinates, center_point, radius)
            ).group_by(
                func.ST_SnapToGrid(Parcel.coordinates, grid_size)
            ).all()

            clusters = [{'x': result.x, 'y': result.y, 'id': result.count} for result in results]'''

    if clusters:
        # results = [{'id': _.id, 'x': _[1], 'y': _[2]} for _ in _objects]

        '''if zoom > 11:
            # Если zoom больше 11, группируем объекты только если они находятся в одной точке
            results = db.session.query(
                Parcel.id,
                func.ST_X(Parcel.coordinates).label('x'),
                func.ST_Y(Parcel.coordinates).label('y')
            ).all()

            clusters = [{'id': result.id, 'x': result.x, 'y': result.y} for result in results]
        else:
            zoom_coefficient = 2 ** (zoom - 4)
            radius = 400000 / zoom_coefficient
            # zoom = 4
            # Определяем размер сетки в зависимости от zoom
            grid_size = 0.00085 * (2 ** (18 - zoom))
            # distance_threshold = 0.0002 * (2 ** (18 - zoom))

            # Выполняем кластеризацию с использованием функции ST_SnapToGrid
            results = db.session.query(
                func.ST_X(func.ST_Centroid(func.ST_Collect(Parcel.coordinates))).label('x'),
                func.ST_Y(func.ST_Centroid(func.ST_Collect(Parcel.coordinates))).label('y'),
                func.count(Parcel.id).label('count')
            ).filter(
                func.ST_DWithin(Parcel.coordinates, center_point, radius)
            ).group_by(
                func.ST_SnapToGrid(Parcel.coordinates, grid_size)
            ).all()

            clusters = [{'x': result.x, 'y': result.y, 'id': result.count} for result in results]'''

        result = {'status': 'success', 'data': clusters}
    else:
        result = {'status': 'error'}

    return jsonify(result)

    '''results = None
    # Получение данных из запроса
    data = request.form

    if data:

        filters = Filter.query.all()

        lot_trade_gov_query = LotTradeGOV.query.with_entities(LotTradeGOV.id)

        for value in data:
            print(value, '-', data[value])
            if data[value] == 'none' or data[value] == '':
                continue
            for _filter in filters:
                if _filter.filter_parameter != value:
                    continue
                if _filter.parameter_type == 'text' or _filter.parameter_type == 'combo_box' or _filter.parameter_type == 'combo_box_from_list':
                    if _filter.db_table_name == 'lots_trade_gov':
                        lot_trade_gov_query = lot_trade_gov_query.filter(
                            text(f"{_filter.filter_parameter} = '{data[value]}'"))
                elif _filter.parameter_type == 'boolean':
                    if _filter.db_table_name == 'lots_trade_gov':
                        lot_trade_gov_query = lot_trade_gov_query.filter(
                            text(f"{_filter.filter_parameter} = {'True' if data[value] == 'true' else 'False'}"))
                elif _filter.parameter_type == 'date_range':
                    min_value = data[value].split('|')[0]
                    max_value = data[value].split('|')[1]
                    if _filter.db_table_name == 'lots_trade_gov':
                        if min_value:
                            lot_trade_gov_query = lot_trade_gov_query.filter(
                                text(f"{_filter.filter_parameter} >= '{min_value}'"))
                        if max_value:
                            lot_trade_gov_query = lot_trade_gov_query.filter(
                                text(f"{_filter.filter_parameter} <= '{max_value}'"))
                elif _filter.parameter_type == 'double_slider':
                    min_value = data[value].split('|')[0]
                    max_value = data[value].split('|')[1]
                    if _filter.db_table_name == 'lots_trade_gov':
                        lot_trade_gov_query = lot_trade_gov_query.filter(
                            text(f"{_filter.filter_parameter} >= '{min_value}'"),
                            text(f"{_filter.filter_parameter} <= '{max_value}'"))

        results = lot_trade_gov_query.all()

        if results:
            lot_ids = [result.id for result in results]
            _objects = Parcel.query.with_entities(
                Parcel.id,
                func.ST_X(Parcel.coordinates).label('x'),
                func.ST_Y(Parcel.coordinates).label('y')
            ).filter(Parcel.id.in_(lot_ids)).all()
        else:
            _objects = None
    else:
        _objects = Parcel.query.with_entities(
            Parcel.id,
            func.ST_X(Parcel.coordinates).label('x'),
            func.ST_Y(Parcel.coordinates).label('y')
        ).all()

    if _objects:
        results = [{'id': _.id, 'x': _[1], 'y': _[2]} for _ in _objects]
        result = {'status': 'success', 'data': results}
    else:
        result = {'status': 'error'}

    return jsonify(result)'''


@api_bp.route('/update_regions', methods=['POST'])
@login_required
def update_lots_trade_gov_regions():
    if 'file' not in request.files:
        return jsonify({'error': 'Ошибка запроса'})

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'})

    if file:
        try:
            def process_excel_data(_file):
                df = pd.read_excel(_file, skiprows=1)
                for row in df.itertuples(index=False):
                    try:
                        region_code = row[0]
                        federal_district = row[1]
                        region_name = row[2]
                    except Exception as E:
                        print(f'Err: {E}')
                        continue
                    region = LotTradeGOVRegion.query.filter_by(region_code=region_code).first()
                    if region:
                        region.federal_district = federal_district
                        region.region_name = region_name
                        try:
                            db.session.commit()
                        except Exception as E:
                            print(f'Error: {E}. Commit rollback.')
                            db.session.rollback()
                    else:
                        new_region = LotTradeGOVRegion(region_code=region_code, federal_district=federal_district,
                                                       region_name=region_name)
                        db.session.add(new_region)
                        try:
                            db.session.commit()
                        except Exception as E:
                            print(f'Error: {E}. Commit rollback.')
                            db.session.rollback()

            process_excel_data(file)
            return jsonify({'success': 'Файл успешно загружен. Данные обновлены.'})
        except Exception as e:
            return jsonify({'error': str(e)})


@api_bp.route('/update_allowed_use', methods=['POST'])
@login_required
def update_lots_trade_gov_allowed_use():
    if 'file' not in request.files:
        return jsonify({'error': 'Ошибка запроса'})

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'})

    if file:
        try:
            def process_excel_data(_file):
                df = pd.read_excel(_file, skiprows=1)
                for row in df.itertuples(index=False):
                    try:
                        allowed_use = row[0]
                        rubric = row[1]
                    except Exception as E:
                        print(f'Err: {E}')
                        continue
                    region = LotTradeGOVAllowedUse.query.filter_by(allowed_use=allowed_use).first()
                    if region:
                        region.allowed_use = allowed_use
                        region.rubric = rubric
                        try:
                            db.session.commit()
                        except Exception as E:
                            print(f'Error: {E}. Commit rollback.')
                            db.session.rollback()
                    else:
                        new_allowed_use = LotTradeGOVAllowedUse(allowed_use=allowed_use, rubric=rubric)
                        db.session.add(new_allowed_use)
                        try:
                            db.session.commit()
                        except Exception as E:
                            print(f'Error: {E}. Commit rollback.')
                            db.session.rollback()

            process_excel_data(file)
            return jsonify({'success': 'Файл успешно загружен. Данные обновлены.'})
        except Exception as e:
            return jsonify({'error': str(e)})
