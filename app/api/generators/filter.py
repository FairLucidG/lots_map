import os
import pickle
import datetime
from app.api import associations_list

CACHE_DIR = os.path.join(os.getcwd(), 'cache')
os.makedirs(CACHE_DIR, exist_ok=True)


def get_cached_filters(filter_name, query_func):
    cache_file = os.path.join(CACHE_DIR, f"{filter_name}.pickle")

    if os.path.exists(cache_file):
        last_modified = datetime.datetime.fromtimestamp(os.path.getmtime(cache_file))
        if last_modified > datetime.datetime.utcnow() - datetime.timedelta(minutes=15):
            with open(cache_file, 'rb') as f:
                return pickle.load(f)

    filters = query_func()
    with open(cache_file, 'wb') as f:
        pickle.dump(filters, f)
    return filters


def generate_text_filter_html(_filter):
    return f"""
    <div class="form-group col-12 col-md-4 mt-2 mb-2">
        <label for="{_filter.filter_parameter}"><h5>{_filter.name}:</h5></label>
        <input type="text" class="form-control" id="{_filter.filter_parameter}" name="{_filter.filter_parameter}" value="">
    </div>
    """


def generate_combo_box_filter_html(_filter, options):
    options_html = "<option value='none'>--- Не задано ---</option>"
    for value in options:
        if _filter.parameter_type == 'combo_box':
            options_html += f"<option>{value}</option>"
        else:
            assoc_value = associations_list.associations[_filter.filter_parameter][value]
            options_html += f"<option value='{value}'>{assoc_value}</option>"

    return f"""
    <div class="form-group col-12 col-md-4 mt-2 mb-2">
        <label for="{_filter.filter_parameter}"><h5>{_filter.name}:</h5></label>
        <select class="form-control" id="{_filter.filter_parameter}" name="{_filter.filter_parameter}">
            {options_html}
        </select>
    </div>
    """


def generate_boolean_filter_html(_filter):
    return f"""
    <div class="form-group col-12 col-md-4 mt-2 mb-2">
        <label for="{_filter.filter_parameter}"><h5>{_filter.name}:</h5></label>
        <select class="form-control" id="{_filter.filter_parameter}" name="{_filter.filter_parameter}">
            <option value='none'>--- Не задано ---</option>
            <option value='yes'>Да</option>
            <option value='no'>Нет</option>
        </select>
    </div>
    """


def generate_date_range_filter_html(_filter):
    return f"""
    <div class="form-group col-12 col-md-4 mt-2 mb-2">
        <label for="{_filter.filter_parameter}_min"><h5>{_filter.name} (от):</h5></label>
        <input type="date" id="{_filter.filter_parameter}_min" class="form-control"></input>
    </div>
    <div class="form-group col-12 col-md-4 mt-2 mb-2">
        <label for="{_filter.filter_parameter}_max"><h5>{_filter.name} (до):</h5></label>
        <input type="date" id="{_filter.filter_parameter}_max" class="form-control"></input>
    </div>
    <input type="hidden" id="{_filter.filter_parameter}" name="{_filter.filter_parameter}">
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


def generate_double_slider_filter_html(_filter, min_value, max_value):
    return f"""
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