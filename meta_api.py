import json
from datetime import datetime, timedelta
import requests
from config import *
from collections import defaultdict
from database import db
from amocrm_int import *


def get_interests(adset_id):
    url = f"https://graph.facebook.com/v23.0/{adset_id}"
    params = {
        "fields": "targeting,daily_budget",
        "access_token": access_token
    }
    response = requests.get(url, params=params)
    data = response.json()
    body = {}
    interests = ""
    try:
        flexible_spec = data["targeting"]["flexible_spec"]
        for spec in flexible_spec:
            if "interests" in spec:
                for interest in spec["interests"]:
                    interests += f"{interest['name']}, "
        body['interests'] = interests
        body['daily_budget'] = data['daily_budget']
    except KeyError:
        pass

    return body


def get_active_campaigns():
    active_campaigns = []
    url = "https://graph.facebook.com/v23.0/act_1011840574303712/campaigns"
    params = {
        "fields": "id,name,status",
        "access_token": access_token,
        "filtering": '[{"field":"effective_status","operator":"IN","value":["ACTIVE"]}]'
    }
    resp = requests.get(url, params=params)
    data = resp.json()

    for campaign in data['data']:
        active_campaigns.append({"id": campaign['id'], "name": campaign['name']})

    return active_campaigns


def get_status(ad_id):
    url = f"https://graph.facebook.com/v23.0/{ad_id}"
    filtering = [{"field": "ad.id", "operator": "EQUAL", "value": str(ad_id)}]
    params = {
        "fields": "id,name,status",
        "access_token": access_token,
    }
    resp = requests.get(url, params=params)
    data = resp.json()
    # print("adset_id: ", adset_id)
    return data['status']


def _active_adsets():
    """Получить все активные группы объявлений"""

    url = f'https://graph.facebook.com/v23.0/act_1011840574303712/adsets'
    params = {
        'access_token': access_token,
        'fields': 'id,name,status,effective_status,daily_budget,campaign_id',
        'effective_status': json.dumps(['ACTIVE'])  # Фильтр по активному статусу
    }

    active_adsets = []

    while True:
        response = requests.get(url, params=params)
        data = response.json()

        if 'error' in data:
            print(f"API Error: {data['error']}")
            break

        adsets = data.get('data', [])
        active_adsets.extend(adsets)

        # Пагинация
        if 'paging' in data and 'next' in data['paging']:
            url = data['paging']['next']
            params = {}
        else:
            break

    return active_adsets


# print(active_adsets())


def active_creatives():
    url = f'https://graph.facebook.com/v23.0/act_1011840574303712/ads'
    params = {
        'access_token': access_token,
        'fields': 'id,name,status,effective_status,daily_budget,adset_id',
        'effective_status': json.dumps(['ACTIVE'])  # Фильтр по активному статусу
    }

    active_ads_ids = []
    response = requests.get(url, params=params)
    data = response.json()

    ads = data.get('data', [])
    print(data)
    for i in data['data']:
        active_ads_ids.append(i['id'])
    return active_ads_ids

# print(active_creatives())


def get_todays_leads_simple(ad_id, target_date):
    """Простая версия для небольшого количества лидов"""

    start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_next_day = start_of_day + timedelta(days=1)

    start_ts = int(start_of_day.timestamp())
    end_ts = int(start_of_next_day.timestamp()) - 1  # Исключаем следующий день

    print(f"Точные границы: {start_ts} ({start_of_day}) - {end_ts} ({datetime.fromtimestamp(end_ts)})")

    url = f'https://graph.facebook.com/v23.0/{ad_id}/leads'

    filtering = [
        {"field": "time_created", "operator": "GREATER_THAN", "value": start_ts - 1},  # -1 чтобы включить точное время
        {"field": "time_created", "operator": "LESS_THAN", "value": end_ts + 1}  # +1 чтобы включить точное время
    ]

    params = {
        'access_token': access_token,
        'fields': 'id,created_time,field_data',
        'filtering': json.dumps(filtering)
    }

    response = requests.get(url, params=params)
    data = response.json()
    print(data)

    filtered_leads = data['data']
    # for lead in data.get('data', []):
    #     created_time = lead.get('created_time')
    #     if created_time:
    #         lead_date = datetime.strptime(created_time, '%Y-%m-%dT%H:%M:%S%z')
    #         if lead_date.date() == target_date.date():
    #             filtered_leads.append(lead)

    # print(f"API вернул: {len(data.get('data', []))} лидов")
    # print(f"После фильтрации на клиенте: {len(filtered_leads)} лидов")
    # print("leads ", len(filtered_leads[0]['field_data'][0]), filtered_leads)
    numbers = []
    counter = 0

    for lead in filtered_leads:
        number = None

        # Ищем основной номер телефона
        for l in lead['field_data']:
            if l['name'] == "telefon_raqamingiz?":
                number = l['values'][0]
                break

        if number is None:
            continue

        print(f"num {number}")
        numbers.append(number)

        # Проверяем валидность основного номера
        if checking_kval(number) == -1:
            for l in lead['field_data']:
                if l['name'] == "telefon raqamingz?":
                    number = l['values'][0]
                    print("new", number)

        if checking_kval(number) == 1:
            counter += 1

    return counter


t_d = datetime(2025, 8, 5)
# print(get_todays_leads_simple(120215617003830753, t_d))


def get_metrics_from_meta(adset_id):
    timestamp = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    body = [{"field":"adset.id","operator":"EQUAL","value":adset_id}]
    url = (
        f"https://graph.facebook.com/v23.0/act_1011840574303712/insights"
        f"?level=ad"
        f"&fields=campaign_id,adset_id,campaign_name,adset_name,ad_id,ad_name,date_start,date_stop,"
        f"spend,impressions,clicks,ctr,cpm,actions"
        f"&access_token={access_token}&"
        f"time_range[since]=2025-08-09&time_range[until]=2025-08-29&time_increment=1"
        f"&filtering={json.dumps(body)}"
        # f"&filtering=[{{\"field\":\"adset.id\",\"operator\":\"EQUAL\",\"value\":\"{adset_id}\"}}]"
    )

    # print(date_since, timestamp)

    response = requests.get(url)
    data = response.json()
    print(data)

    for row in data["data"]:
        spend = float(row.get("spend", 0))
        impressions = int(row.get("impressions", 0))
        clicks = int(row.get("clicks", 0))

        leads = 0
        actions = row.get('actions', [])
        for action in actions:
            if action.get("action_type") == 'lead':
                leads = action.get('value', 0)
            # if action["action_type"] in ["lead", "onsite_conversion.lead_grouped"]:
            #     leads += int(action.get("value", 0))

        timestamp = row['date_stop'].split("-")
        year = int(timestamp[0])
        month = int(timestamp[1])
        day = int(timestamp[2])
        target_date = datetime(year, month, day)
        kval_leads = get_todays_leads_simple(row['ad_id'], target_date)

        cr = round(int(leads) / clicks, 4) if clicks > 0 else 0
        cpl = round(spend / int(leads), 4) if int(leads) > 0 else 0
        ctr = round(clicks / impressions * 100, 4) if impressions > 0 else 0
        cpm = round(spend / impressions * 1000, 4) if impressions > 0 else 0

        timestamp = row['date_stop']

        # lst.append(row["adset_id"])

        params = (
            row["adset_id"],
            row['adset_name'],
            row["ad_name"],
            row['ad_id'],
            timestamp,
            spend,
            impressions,
            clicks,
            leads,
            cr,
            cpl,
            ctr,    
            cpm,
            kval_leads
        )
        # print(params)
        db.insert_new_ad_metrics(params=params)


# get_metrics_from_meta(120222675430710753)


def get_metrics_for_day():
    additions = []
    url = "https://graph.facebook.com/v23.0/act_1011840574303712/insights"

    timestamp = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")

    params = {
        "level": "ad",
        "fields": "campaign_id,adset_id,campaign_name,adset_name,ad_id,ad_name,date_start,date_stop,"
                  "spend,impressions,clicks,ctr,cpm,actions",
        "access_token": access_token,
        "time_range[since]": timestamp,
        "time_range[until]": timestamp,
        "time_increment": 1,
        # "filtering": f'[{{"field": "campaign.id", "operator": "EQUAL", "value": {campaign_id}}}]'
    }

    # print(date_since, timestamp)

    response = requests.get(url, params=params)
    data = response.json()
    print(data)

    for row in data["data"]:
        if get_status(row['ad_id']) == "ACTIVE":
            spend = float(row.get("spend", 0))
            impressions = int(row.get("impressions", 0))
            clicks = int(row.get("clicks", 0))

            leads = 0
            actions = row.get('actions', [])
            for action in actions:
                if action.get("action_type") == 'lead':
                    leads = action.get('value', 0)
                # if action["action_type"] in ["lead", "onsite_conversion.lead_grouped"]:
                #     leads += int(action.get("value", 0))

            timestamp = row['date_stop'].split("-")
            year = int(timestamp[0])
            month = int(timestamp[1])
            day = int(timestamp[2])
            target_date = datetime(year, month, day)
            kval_leads = get_todays_leads_simple(row['ad_id'], target_date)

            cr = round(int(leads) / clicks, 4) if clicks > 0 else 0
            cpl = round(spend / int(leads), 4) if int(leads) > 0 else 0
            ctr = round(clicks / impressions * 100, 4) if impressions > 0 else 0
            cpm = round(spend / impressions * 1000, 4) if impressions > 0 else 0

            timestamp = row['date_stop']

            # lst.append(row["adset_id"])

            params = (
                row["adset_id"],
                row['adset_name'],
                row["ad_name"],
                row['ad_id'],
                timestamp,
                spend,
                impressions,
                clicks,
                leads,
                cr,
                cpl,
                ctr,
                cpm,
                kval_leads
            )
            # print(params)
            db.insert_new_ad_metrics(params=params)

# get_metrics_for_day()


def get_metrics_from_db(adset_id):
    metrics = db.get_metrics_by_adset_id(adset_id)

    # grouped[ad_id] = {"adset_name": adset_name, "ad_name": ad_name, "rows": [...]}
    grouped = defaultdict(lambda: {"adset_name": "", "ad_name": "", "rows": []})

    for row in metrics:
        ad_id = row[4]  # ad_id теперь на 4-й позиции
        adset_name = row[2]  # adset_name на 2-й позиции
        ad_name = row[3]  # ad_name на 3-й позиции

        grouped[ad_id]["adset_name"] = adset_name
        grouped[ad_id]["ad_name"] = ad_name
        grouped[ad_id]["rows"].append(row)

    full_text = ""
    for ad_id, data in grouped.items():
        adset_name = data["adset_name"]
        ad_name = data["ad_name"]

        # Получаем adset_id из первой строки для проверки статуса
        first_row = data["rows"][0]
        adset_id = first_row[1]

        if get_status(ad_id) == "ACTIVE":
            body = get_interests(int(adset_id))
            full_text += (f"### Ad ID: {ad_id} — {ad_name} (AdSet: {adset_name})\n"
                          f"Интересы: {body['interests']}. \n"
                          f"Daily_budget: {body['daily_budget']} центов.\n\n")

            full_text += ("| Date | Потрачено, $ | Impressions | Clicks | Leads | CR | CPL | CTR | CPM | Kval Leads |\n"
                          "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")

            # r: (id, adset_id, adset_name, ad_name, ad_id, timestamp, spend, impressions, clicks, leads, cr, cpl, ctr, cpm, kval_leads)
            #     0    1        2           3        4      5          6      7            8       9      10  11   12   13   14
            for r in data["rows"]:
                full_text += (
                    f"| {r[5]} | {r[6]} | {r[7]} | {r[8]} | {r[9]} | {r[10]} | {r[11]} | {r[12]} | {r[13]} | {r[14]} |\n"
                )
            full_text += "\n\n---\n\n"

    return full_text

print(get_metrics_from_db(120215616952620753))