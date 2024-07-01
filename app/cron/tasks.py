import re
import ast
import time
import pytz
import requests
from sqlalchemy import asc
from app import db, scheduler
from datetime import datetime, timedelta
from app.models import LotTradeGOV, CategoryTradeGOV, Parcel, LandParcelManager

from rosreestr2coord import Area

from pypac import PACSession, get_pac

pac_url = "https://p.thenewone.lol:8443/proxy.pac"


def decrease_date(date_str, days):
    # Преобразуем строку с датой в объект datetime
    date_object = datetime.strptime(date_str, '%Y-%m-%d')

    # Уменьшаем дату на 1 день
    new_date = date_object - timedelta(days=days)

    # Преобразуем новую дату обратно в строку в нужном формате
    new_date_str = new_date.strftime('%Y-%m-%d')

    return new_date_str


def add_global_parse_job(category_id, _scheduler):
    _scheduler.add_job(
        id=f'parse_job_{category_id}_global',
        func=parse_category_global,
        trigger='interval',
        minutes=20160,  # 14 days
        misfire_grace_time=900,
        replace_existing=True,
        next_run_time=datetime.now(),
        kwargs={'category_id': category_id, '_scheduler': _scheduler}
    )


def add_parse_job(category_id, _scheduler):
    _scheduler.add_job(
        id=f'parse_job_{category_id}',
        func=parse_category,
        trigger='interval',
        minutes=120,
        misfire_grace_time=900,
        replace_existing=True,
        next_run_time=datetime.now(),
        kwargs={
            'category_id': category_id,
            'pubTo': datetime.now().strftime('%Y-%m-%d'),
            'pubFrom': decrease_date(datetime.now().strftime('%Y-%m-%d'), 1),
            '_scheduler': _scheduler
        }
    )


def parse_category_global(category_id, _scheduler):

    date_to = '2023-07-28'  # datetime.now().strftime('%Y-%m-%d')
    date_from = decrease_date(date_to, 1)

    min_date = '2021-12-30'
    print(f'get {category_id}')

    while datetime.strptime(min_date, '%Y-%m-%d') < datetime.strptime(date_to, '%Y-%m-%d'):
        print(f'from {date_from}')
        parse_category(category_id, date_to, date_from, _scheduler)
        print('success')
        date_to = decrease_date(date_to, 2)
        date_from = decrease_date(date_from, 2)

        # time.sleep(3)
        time.sleep(3)


def parse_category(category_id, pubTo, pubFrom, _scheduler):
    page = 0
    while True:
        print('get_data')
        response = get_data(category_id, pubTo, pubFrom, page)
        print(response)
        print('данные получены')
        parse_data(response, _scheduler)
        print('обработаны')

        if response['last']:
            break

        page += 1
        # задержка 1.5 секунды между запросами
        # time.sleep(1.5)
        time.sleep(0.7)


def get_data(category, pubTo, pubFrom, page):
    url = "https://torgi.gov.ru/new/api/public/lotcards/search"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/58.0.3029.110 Safari/537.3'}

    params = {
        'catCode': category,
        'byFirstVersion': 'true',
        'withFacets': 'true',
        'size': 100,
        'page': page,
        'pubTo': pubTo,
        'pubFrom': pubFrom,
        'sort': 'firstVersionPublicationDate,desc'
    }

    pac = get_pac(url=pac_url)
    session = PACSession(pac)

    # response = requests.get(url, params=params, headers=headers, timeout=5)
    try:
        response = session.get(url, params=params, headers=headers, timeout=5)
    except Exception as e:
        print("Error:", e)
        time.sleep(1)
        get_data(category, pubTo, pubFrom, page)
        return

    return response.json()


def parse_data(response, _scheduler):
    parsed_data = []
    for item in response['content']:
        lot_id = item['id']
        with _scheduler.app.app_context():
            lot_model = LotTradeGOV.query.get(lot_id)
            if lot_model:
                time.sleep(0.1)
                continue
        get_lot_data(lot_id, _scheduler)
        # time.sleep(3.7)
        time.sleep(0.3)
    return parsed_data


def get_lot_data(lot_id, _scheduler):
    url = f"https://torgi.gov.ru/new/api/public/lotcards/{lot_id}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/58.0.3029.110 Safari/537.3'}

    pac = get_pac(url=pac_url)
    session = PACSession(pac)

    try:
        # response = requests.get(url, headers=headers, timeout=3)
        response = session.get(url, headers=headers, timeout=3)
    except Exception as e:
        # except requests.exceptions.RequestException as e:
        print("Error:", e)
        time.sleep(1)
        get_lot_data(lot_id, _scheduler)
        return

    data = response.json()

    lot_data = {
        "id": data.get("id"),
        "lot_name": data.get("lotName"),
        "lot_status": data.get("lotStatus"),
        "bidd_form": data.get("biddForm", {}).get("name"),
        "notice_number": data.get("noticeNumber"),
        "lot_number": data.get("lotNumber"),
        "bidd_type": data.get("biddType", {}).get("name"),
        "subject_rf_code": data.get("subjectRFCode"),
        "lot_description": data.get("lotDescription"),
        "price_min": data.get("priceMin"),
        "price_step": data.get("priceStep"),
        "currency_code": data.get("currencyCode"),
        "etp_code": data.get("etpCode"),
        "category": data.get("category", {}).get("name"),
        "time_zone_name": data.get("timeZoneName"),
        "timezone_offset": data.get("timezoneOffset"),
        "ownership_form": data.get("ownershipForm", {}).get("name"),
        "etp_url": data.get("etpUrl"),
        "deposit": data.get("deposit"),
        "estate_address": data.get("estateAddress"),
        "has_appeals": data.get("hasAppeals"),
        "is_stopped": data.get("isStopped"),
        "auction_start_date": data.get("auctionStartDate"),
        "bidd_start_time": data.get("biddStartTime"),
        "bidd_end_time": data.get("biddEndTime"),
        "version_id": data.get("versionId"),
        "is_annulled": data.get("isAnnulled"),
        "lot_vat": data.get("lotVat", {}).get("name"),
        "npa_hint_code": data.get("npaHintCode"),
        "type_transaction": data.get("typeTransaction"),
        "permitted_use": None,
        "contract_type": None,
        "cadaster_number": None,
        "area": None,
        "url": None,
        "last_updated": datetime.now(pytz.utc),
        #"final_price": data.get("finalPrice"),
        "rent_period": None,
        "rent_term": None,
        "auction_step_percent": None,
        "deposit_percent": None,
        "recipient": None,
        "recipient_inn": None,
        "deposit_rules": None,
        "deposit_return_rules": None,
        "deposit_electronic_platform": data.get("depositElectronicPlatform"),
        "deposit_recipient_name": data.get("depositRecipientName"),
        "deposit_recipient_inn": data.get("depositRecipientINN"),
        "deposit_recipient_kpp": data.get("depositRecipientKPP"),
        "deposit_bank_name": data.get("depositBankName"),
        "deposit_bik": data.get("depositBIK"),
        "deposit_pay_account": data.get("depositPayAccount"),
        "deposit_cor_account": data.get("depositCorAccount"),
        "deposit_purpose_payment": data.get("depositPurposePayment"),
    }

    # Обработка characteristics
    for characteristic in data["characteristics"]:
        if characteristic["code"] == "PermittedUse":
            lot_data["permitted_use"] = ", ".join(
                [value["name"] for value in characteristic.get("characteristicValue", [])])
        elif characteristic["code"] == "CadastralNumber":
            lot_data["cadaster_number"] = characteristic.get("characteristicValue")
        elif characteristic["code"].startswith("Square"):
            lot_data["area"] = characteristic.get("characteristicValue")
        elif characteristic["code"] == "regNumberEGROKN":
            lot_data["reg_number_egrokn"] = characteristic.get("characteristicValue")

    # Обработка attributes
    for attribute in data["attributes"]:
        attribute_value = None
        if 'value' in attribute:
            if attribute['attributeType'].startswith('Text'):
                attribute_value = attribute.get('value')
            elif attribute['attributeType'].startswith('Select'):
                attribute_value = attribute.get('value')
                if attribute_value:
                    attribute_value = attribute_value.get('name')
            else:
                attribute_value = attribute.get('value')

        if attribute["code"] == "DA_contractType_EA(ZK)":
            lot_data["contract_type"] = attribute_value
        elif attribute["code"] == "DA_contractSignPeriod__EA(ZK)":
            lot_data["rent_period"] = attribute_value
        elif attribute["code"] == "DA_contractDate_EA(ZK)":
            lot_data["rent_term"] = attribute_value
        elif attribute["code"] == "DA_auctionStepPercent_EA(ZK)":
            lot_data["auction_step_percent"] = attribute_value
        elif attribute["code"] == "DA_depositPercent_EA(ZK)":
            lot_data["deposit_percent"] = attribute_value
        elif attribute["code"] == "DA_recipient_EA(ZK)":
            lot_data["recipient"] = attribute_value
        elif attribute["code"] == "DA_recipientINN_EA(ZK)":
            lot_data["recipient_inn"] = attribute_value
        elif attribute["code"] == "DA_depositTimeAndRules_EA(ZK)":
            lot_data["deposit_rules"] = attribute_value
        elif attribute["code"] == "DA_depositReturnRules_EA(ZK)":
            lot_data["deposit_return_rules"] = attribute_value
        elif attribute["code"] == "DA_landRestrictions_EA(ZK)":
            lot_data["land_restrictions"] = attribute_value
        elif attribute["code"] == "DA_contractSignPeriod__EA(ZK)":
            lot_data["contract_sign_period"] = attribute_value
        elif attribute["code"] == "DA_constructionParametersMax_EA(ZK)":
            lot_data["construction_parameters_max"] = attribute_value
        elif attribute["code"] == "DA_constructionParametersMin_EA(ZK)":
            lot_data["construction_parameters_min"] = attribute_value
        elif attribute["code"] == "DA_connectionETSN_EA(ZK)":
            lot_data["connection_etsn"] = attribute_value
        elif attribute["code"] == "DA_participationFee_EA(ZK)":
            lot_data["participation_fee"] = attribute_value
        elif attribute["code"] == "DA_depositRefund_EA(ZK)":
            lot_data["deposit_refund"] = attribute_value
        elif attribute["code"] == "DA_forSmallBusiness_EA(ZK)":
            lot_data["forSmallBusiness"] = 'Только для МСП'

    # Формирование ссылки на торги
    lot_data["url"] = f"https://torgi.gov.ru/new/public/lots/lot/{data['noticeNumber']}_{data['lotNumber']}"

    # Обработка protocols
    protocols = data.get("protocols", [])
    for protocol in protocols:
        if protocol["type"]["code"].startswith("AUCTION_RESULTS"):
            results = protocol.get("results", [])
            if results:
                for res in results:
                    is_first = res.get('isFirst', False)
                    if not is_first:
                        continue
                    lot_data["protocol_results_participant_price"] = res.get("participantPrice")
                    lot_data["protocol_results_order_number"] = res.get("orderNumber")
                    lot_data["protocol_results_full_name"] = res.get("fullName")
                    lot_data['protocol_results_lastName'] = res.get("lastName", '')
                    lot_data['protocol_results_firstName'] = res.get("firstName", '')
                    lot_data['protocol_results_middleName'] = res.get("middleName", '')
                    lot_data['protocol_results_orgType'] = res.get("orgType", '')
                    lot_data["protocol_results_inn"] = res.get("inn")
                    lot_data["protocol_results_kpp"] = res.get("kpp")
                    break

    # Получаем или создаем экземпляр модели LotTradeGOV
    with _scheduler.app.app_context():
        lot_model = LotTradeGOV.query.get(lot_id)
        if lot_model:
            # Обновляем существующий экземпляр
            for key, value in lot_data.items():
                setattr(lot_model, key, value)
        else:
            # Создаем новый экземпляр
            lot_model = LotTradeGOV(**lot_data)
            db.session.add(lot_model)

        try:
            db.session.commit()
        except Exception as E:
            print(f'Error: {E}. Commit rollback.')
            db.session.rollback()


def find_cadastral_number(text):
    # Шаблон для поиска кадастрового номера
    pattern = r'\b(\d+:\d+(:\d+(:\d+)?)?)\b'

    # Поиск всех вхождений кадастрового номера в тексте
    matches = re.findall(pattern, text)

    # Если найдено хотя бы одно совпадение, возвращаем первый найденный кадастровый номер
    if matches:
        return matches[0][0]
    else:
        return None


def clean_cadastral_number(cadastral_number):
    parts = cadastral_number.split(':')  # Разбиваем кадастровый номер на части

    # Убираем лишние нули в начале каждой части и лишние символы в конце
    cleaned_parts = [part.lstrip('0').rstrip('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz') for part in parts]

    # Убираем последнюю часть, если она состоит только из нулей
    while cleaned_parts and cleaned_parts[-1] == '0':
        cleaned_parts.pop()

    # Собираем очищенный кадастровый номер из частей
    cleaned_cadastral_number = ':'.join(cleaned_parts)

    return cleaned_cadastral_number


def get_coordinates(cadastral_number):
    url = f"https://pkk.rosreestr.ru/api/features/1/{cadastral_number}"

    # Отправляем GET-запрос
    response = requests.get(url, verify=False)

    # Проверяем успешность запроса
    if response.status_code == 200:
        # Преобразуем ответ в JSON
        data = response.json()

        # Проверяем, есть ли поле feature и оно не равно null
        if 'feature' in data and data['feature'] is not None:
            # Проверяем наличие поля center и полей x и y в нем
            if 'center' in data['feature'] and 'x' in data['feature']['center'] and 'y' in data['feature']['center']:
                # Возвращаем координаты
                return data['feature']['center']['x'], data['feature']['center']['y']
            else:
                print("Не удалось найти координаты")
        else:
            print("Не удалось найти объект с данным кадастровым номером")
    else:
        print("Ошибка при выполнении запроса")
    return None, None


def additional_lot_info_task(_scheduler, _db):
    with _scheduler.app.app_context():
        lot_models = _db.session.query(LotTradeGOV).\
            filter(LotTradeGOV.cadaster_number != '', LotTradeGOV.coordinates == '').\
            order_by(asc(LotTradeGOV.last_updated)).limit(500).all()

        for lot in lot_models:
            try:
                try:
                    print(lot.cadaster_number)
                    # Создание объекта Area с кадастровым номером участка
                    cadaster_number = find_cadastral_number(lot.cadaster_number)
                    if cadaster_number is None:
                        continue
                    area = Area(clean_cadastral_number(cadaster_number))
                    polygon = area.get_coord()
                    if polygon:
                        polygon = str(polygon[0][0])
                    else:
                        polygon = None
                    center = area.get_center_xy()
                    if center:
                        center = str(center[0][0][0])
                    else:
                        center = None
                    attr = str(area.get_attrs())

                    lot.coordinates = center if center else ''
                    lot.polygon = polygon if polygon else ''
                    lot.additional_info = attr if attr else ''

                    try:
                        db.session.commit()
                    except Exception as E:
                        print(f'Error: {E}. Commit rollback.')
                        db.session.rollback()

                    if center:
                        _coord = ast.literal_eval(center)
                        print(f'{lot.id}: {center}')

                        if polygon:
                            polygon_coordinates = ast.literal_eval(polygon)

                            point = f'POINT({_coord[0]} {_coord[1]})'
                            if len(polygon_coordinates) > 2:
                                polygon_wkt = 'POLYGON((' + ', '.join(
                                    [f'{coord[0]} {coord[1]}' for coord in polygon_coordinates]) + ', ' + str(
                                    polygon_coordinates[0][0]) + ' ' + str(polygon_coordinates[0][1]) + '))'
                            else:
                                polygon_wkt = None
                            new_parcel = Parcel(id=lot.id,
                                                coordinates=point,
                                                polygon=polygon_wkt
                                                )
                            db.session.add(new_parcel)

                            try:
                                db.session.commit()
                            except Exception as E:
                                print(f'Error: {E}. Commit rollback.')
                                db.session.rollback()

                    if attr:
                        _attr = ast.literal_eval(attr)

                        # Создание нового объекта LandParcel
                        manager = LandParcelManager(_attr, lot.id)
                        try:
                            manager.create_new_parcel()
                        except Exception as E:
                            print(f'Error: {E}. Commit rollback.')
                            db.session.rollback()

                    time.sleep(1)
                finally:
                    lot.last_updated = datetime.now(pytz.utc)
                    db.session.commit()

            except Exception as E:
                print(f'Error: {E}')
                lot.last_updated = datetime.now(pytz.utc)
                print(f'Установлена дата {lot.last_updated} для {lot.id}. DateUTC: {datetime.now(pytz.utc)}')
                db.session.commit()
                print('Commit')
                continue


def add_additional_lot_info_task_job(_scheduler, _db):
    _scheduler.add_job(
        id=f'additional_lot_info_task',
        func=additional_lot_info_task,
        trigger='interval',
        minutes=15,
        misfire_grace_time=900,
        next_run_time=datetime.now(),  # datetime.now(pytz.utc) + timedelta(minutes=60),
        replace_existing=True,
        kwargs={'_scheduler': _scheduler, '_db': _db}
    )
