function get_filters() {
    $.ajax({
            url: "/api/get_filters",
            type: "GET",
            success: function(response) {
                let json_response = response;
                if( json_response.status == 'success') {
                    data = json_response.data;
                    $('#filters').html(data);
                }
            },
            error: function(xhr, status, error) {
                // Обработка ошибки
                console.error("Ошибка при выполнении запроса:", status, error);
            }
        });
}

function loadTableData(page) {
    const perPage = 10; // Количество элементов на странице
    const formData = new FormData(document.getElementById('home_filter_form'));

    fetch(`/api/get_lots_by_filters?page=${page}&per_page=${perPage}&table=true`, {
        method: 'POST',
        body: formData
    })
        .then(response => response.json())
        .then(data => {
            const tableBody = document.getElementById('table-body');
            tableBody.innerHTML = '';
            data.table_data.forEach(row => {
                const tr = document.createElement('tr');
                const paramTd = document.createElement('td');
                const valueTd = document.createElement('td');
                paramTd.textContent = row.param;
                valueTd.textContent = row.value;
                value2Id.textContent = row.value;
                tr.appendChild(paramTd);
                tr.appendChild(valueTd);
                tableBody.appendChild(tr);
            });

            const pagination = document.getElementById('pagination');
            pagination.innerHTML = '';
            if (data.pagination.pages.length > 1) {
                if (page > 1) {
                    const prevLi = document.createElement('li');
                    prevLi.classList.add('page-item');
                    prevLi.innerHTML = `<a class="page-link" href="#" data-page="${page - 1}">«</a>`;
                    pagination.appendChild(prevLi);
                } else {
                    const prevLi = document.createElement('li');
                    prevLi.classList.add('page-item', 'disabled');
                    prevLi.innerHTML = `<a class="page-link" href="#">«</a>`;
                    pagination.appendChild(prevLi);
                }

                for (let i = 0; i < data.pagination.pages.length; i++) {
                    let pageLi = document.createElement('li');
                    let pageNumber = data.pagination.pages[i];
                    pageLi.classList.add('page-item');
                    if( pageNumber === page ) {
                        pageLi.classList.add('active');
                    }
                    if ( pageNumber === null ) {
                        pageNumber = '...';
                        pageLi.classList.add('disabled');
                    }
                    pageLi.innerHTML = `<a class="page-link" href="#" data-page="${pageNumber}">${pageNumber}</a>`;
                    pagination.appendChild(pageLi);
                }

                if (page < data.pagination.pages[data.pagination.pages.length-1]) {
                    const nextLi = document.createElement('li');
                    nextLi.classList.add('page-item');
                    nextLi.innerHTML = `<a class="page-link" href="#" data-page="${page + 1}">»</a>`;
                    pagination.appendChild(nextLi);
                } else {
                    const nextLi = document.createElement('li');
                    nextLi.classList.add('page-item', 'disabled');
                    nextLi.innerHTML = `<a class="page-link" href="#">»</a>`;
                    pagination.appendChild(nextLi);
                }
            }

            document.querySelectorAll('#pagination a').forEach(link => {
                link.addEventListener('click', function(e) {
                    e.preventDefault();
                    const page = parseInt(this.getAttribute('data-page'));
                    loadTableData(page);
                });
            });
        });
}

$(document).ready(function() {
    /*
        Код выполняющийся после загрузки страницы
    */
});


var lotsMap;

function init() {

    const  lotsMap = new ymaps.Map("map", {
        center: [61.698653, 99.505405], // Центр России
        zoom: 4, // Масштаб, при котором вся Россия видна
        //controls: []
    });

    toggleViewBtn.addEventListener('click', function() {
        lotsMap.container.fitToViewport();
    });

    //myMap.controls.add('typeSelector');

    // Создание ObjectManager
    var objectManager = new ymaps.ObjectManager({
        clusterize: true, // Включаем кластеризацию
        gridSize: 64, // Размер ячейки сетки, в пикселях
        clusterDisableClickZoom: true, // Отключаем приближение карты при клике на кластер
        clusterOpenBalloonOnClick: false // Отключаем открытие балуна при клике на кластер
    });

    // Метод создания массива объектов точек для карты
    function generate_points(_objects) {

        features = [];

        addRow('Результаты поиска', 'Найдено объектов на карте: ' + _objects.length);

        for(let i=0; i < _objects.length; i++) {

            features.push(
                {
                    "type": "Feature",
                    "id": _objects[i].id,
                    "geometry": {
                        "type": "Point",
                        "coordinates": [ _objects[i].y , _objects[i].x ]
                    },
                    "properties": {
                        "hintContent": _objects[i].count,  //"Нажмите для получения дополнительной информации",
                        "balloonContentHeader": "<font size=3><b>_objects[i].count</b></font>",
                        "balloonContentBody": "<p>{{ obj.bidd_form }}</p><a href='#' target='_blank'>Подробнее о лоте</a>",
                        "balloonContentFooter": "<font size=1>Информация предоставлена <a href='https://mycotka.ru'>mycotka.ru</a></font>",
                        "lot_category": "{{ obj.category }}",
                        "lot_description": "{{ obj.lot_description }}"
                    }
                }
            );
        }

        return {
            "type": "FeatureCollection",
            "features": features
        }
    }

    // Метод получения точек на карте
    function get_objects(formData = null) {

        lotsMap.geoObjects.removeAll();
        objectManager.removeAll();

        clearTable();

        let bounds = lotsMap.getBounds();
        let bounds_str = bounds[0][0] + ',' + bounds[1][0] + ',' + bounds[0][1] + ',' + bounds[1][1]
        let center = lotsMap.getCenter()
        let center_str = center[1] + ',' + center[0]

        // Отправляем AJAX-запрос
        $.ajax({
            type: 'POST',
            url: `/api/get_lots_by_filters?zoom=${lotsMap.getZoom()}&bounds=${bounds_str}&center=${center_str}`,
            data: formData,
            success: function(response) {
                if( response.status == 'success') {
                    // -- разделить на части по 1000 за раз подгрузка --
                    objectManager.add(generate_points(response.data));
                    lotsMap.geoObjects.add(objectManager);
                }
            },
            error: function(xhr, status, error) {
                // Обработка ошибок
                console.error('Error get objects');
            }
        });

    }

    // Кнопка поиска по фильтрам
    $('#home_filter_form').submit(function(e) {

        e.preventDefault(); // Предотвращаем стандартное поведение отправки формы

        // Получаем данные формы
        let formData = $(this).serialize();

        // обновляем метки на карте
        get_objects(formData);
    });

    // При инициализации загружаем объекты карты
    get_objects();

    // Функция для очистки таблицы
    function clearTable() {
        // Получаем ссылку на таблицу по ID
        let table = document.getElementById('attrTable');
        table.getElementsByTagName('tbody')[0].innerHTML = '';
    }

    // Функция для добавления пары заголовок-значение
    function addRow(header, value) {
        addHeaderRow(header);
        addValueRow(value);
    }

    function addHeaderRow(header) {
        let table = document.getElementById('attrTable');
        var tbody = table.getElementsByTagName('tbody')[0];
        var headerRow = tbody.insertRow();
        headerRow.innerHTML = '<th>' + header + '</th>';
    }

    function addValueRow(value, title='', idx=0) {
        let table = document.getElementById('attrTable');
        var tbody = table.getElementsByTagName('tbody')[0];
        var valueRow = tbody.insertRow();
        var valueCell = valueRow.insertCell(0);

        valueCell.innerHTML = '<div tabindex="' + idx +
                                '" data-bs-toggle="popover" data-bs-trigger="hover focus" data-bs-content="'
                                    + title + '">' + value + '</div>';
    }

    // Подписываемся на событие клика по метке или кластеру
    /*objectManager.objects.events.add('click', function (e) {

        var objectId = e.get('objectId');
        var object = objectManager.objects.getById(objectId);

        lotsMap.setCenter(object.geometry.coordinates, lotsMap.getZoom(), { duration: 300 });

        clearTable();

        // Выполнение AJAX-запроса с использованием jQuery
        $.ajax({
            url: "/api/get_lot_attr/" + objectId,
            type: "GET",
            success: function(response) {
                let json_response = response; // JSON.parse(decoded_text);
                if( json_response.status == 'success') {
                    data = json_response.data;
                    for(let i = 0; i < data.length; i++) {
                        addValueRow(data[i].value, data[i].param, i);
                        if( data[i].script !== undefined ) {
                            eval(data[i].script)
                        }
                    }
                    $('[data-bs-toggle="popover"]').popover({
                        //Установление направления отображения popover
                        placement : 'right'
                    });
                }
            },
            error: function(xhr, status, error) {
                console.log(error);
                // Обработка ошибки
                console.error("Ошибка при выполнении запроса:", status, error);
            }
        });
    });*/

    // Подписываемся на событие изменения масштаба карты
    lotsMap.events.add('boundschange', function (e) {

        var newZoom = e.get('newZoom');
        var polygonCollection = new ymaps.GeoObjectCollection();

        // Получаем данные формы
        let formData = $('#home_filter_form').serialize();

        // обновляем метки на карте
        get_objects(formData);

        // Если масштаб карты больше или равен 15 (приблизительно 300м)
        if (newZoom >= 15) {
            // Добавляем полигоны в коллекцию
            /*polygons.forEach(function (polygon) {
                polygonCollection.add(polygon);
            });
            // Добавляем коллекцию на карту
            myMap.geoObjects.add(polygonCollection);*/
        } else {
            // Удаляем коллекцию с карты при отдалении
            lotsMap.geoObjects.remove(polygonCollection);
        }
    });
}