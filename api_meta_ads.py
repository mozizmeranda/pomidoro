import json
import markdown
from amocrm_int import *
from environs import Env
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
import requests
from collections import defaultdict
from datetime import datetime, timedelta
from database import db
import json

env = Env()
env.read_env()

app_id = env.str("APP_ID")
app_secret = env.str("APP_SECRET")
access_token = env.str("ACCESS_TOKEN")
ad_account_id = 'act_1011840574303712'  # Sherzod Djalilov

FacebookAdsApi.init(app_id, app_secret, access_token)

# FacebookAdsApi.init(app_id, app_secret, access_token)
my_account = AdAccount(ad_account_id)


def llm_create_campaign(name: str, daily_budget):
    try:
        campaign = my_account.create_campaign(
            params={
                'name': name,
                'objective': 'OUTCOME_ENGAGEMENT',  # или REACH, TRAFFIC, CONVERSIONS и т.д.
                'status': 'PAUSED',  # 'ACTIVE' чтобы сразу запустить
                'daily_budget': int(daily_budget),
                'special_ad_categories': []  # [] если не финанс/жильё/политика
            }
        )

        print(campaign)
        return campaign
    except Exception as e:
        print(e)


def llm_create_adset(name: str, campaign_id: int, audience_id: int):
    try:
        l = {
            'name': name,
            'campaign_id': campaign_id,

            # Место получения конверсий: Instagram
            'destination_type': 'INSTAGRAM_DIRECT',

            # Цель по результативности: "максимальное количество лидов"
            'optimization_goal': 'CONVERSATIONS',

            'billing_event': 'IMPRESSIONS',
            'bid_strategy': 'LOWEST_COST_WITHOUT_CAP',
            'bid_amount': 100,

            # Promoted object для messaging
            'promoted_object': {
                'page_id': None
            },

            # Таргетинг
            'targeting': {
                'geo_locations': {'countries': ['UZ']},  # Обязательно!
                'publisher_platforms': ['instagram'],  # Только Instagram
                'instagram_positions': ['stream'],  # Лента профиля Instagram
            },

            # ID вашей аудитории
            'targeting_audience_id': audience_id,

            'status': 'PAUSED'
        }

        set = my_account.create_ad_set(params=l)
        # print(set)
        return set

    except Exception as e:
        print(e)


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


# print(get_interests(120215617003820753))

def get_status(adset_id):
    url = f"https://graph.facebook.com/v23.0/{adset_id}"
    filtering = [{"field": "adset.id", "operator": "EQUAL", "value": str(adset_id)}]
    params = {
        "fields": "id,name,status",
        "access_token": access_token,
    }
    resp = requests.get(url, params=params)
    data = resp.json()
    print("adset_id: ", adset_id)
    return data['status']


def set_adset_status(adset_id, status):
    """
    status: 'ACTIVE' или 'PAUSED'
    """
    url = f"https://graph.facebook.com/v23.0/{adset_id}"
    params = {
        "status": status,
        "access_token": access_token
    }
    response = requests.post(url, data=params)
    return response.json()


def update_adset_budget(adset_id, daily_budget_usd):
    """
    daily_budget_usd — в долларах, конвертируем в центы (Facebook принимает в минимальных единицах валюты)
    """
    budget_in_cents = int(daily_budget_usd)
    url = f"https://graph.facebook.com/v23.0/{adset_id}"
    params = {
        "daily_budget": budget_in_cents,
        "access_token": access_token
    }
    response = requests.post(url, data=params)
    return response.json()


def get_adset_name_by_id(adset_id):
    url = f"https://graph.facebook.com/v23.0/{adset_id}"
    params = {
        "fields": "name,daily_budget",
        "access_token": access_token,
    }
    resp = requests.get(url, params=params).json()
    return resp


# print(get_adset_name_by_id("120215616952620753"))

def get_campaign_name(campaign_id):
    url = f"https://graph.facebook.com/v23.0/{campaign_id}"
    params = params = {
        "fields": "id,name",
        "access_token": access_token,
    }
    resp = requests.get(url, params=params)
    data = resp.json()
    return data['name']


def get_metrics_from_db(campaign_id):
    metrics = db.get_metrics(campaign_id)

    # grouped[adset_id] = {"name": adset_name, "rows": [..]}
    grouped = defaultdict(lambda: {"name": "", "rows": []})
    for row in metrics:
        adset_id = row[1]
        adset_name = row[2]
        grouped[adset_id]["name"] = adset_name
        grouped[adset_id]["rows"].append(row)

    full_text = ""
    for adset_id, data in grouped.items():
        if get_status(adset_id) == "ACTIVE":
            body = get_interests(int(adset_id))
            full_text += (f"### Adset ID: {adset_id} — {data['name']}.\n Интересы: {body['interests']}. \n"
                          f"Daily_budget: {body['daily_budget']} центов.\n\n")
            full_text += "| Date | Потрачено, $ | Impressions | Clicks | Leads | CR | CPL | CTR | CPM |\n"
            full_text += "| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"

        # r: (id, adset_id, adset_name, campaign_id, timestamp, spend, impressions, clicks, leads, cr, cpl, ctr, cpm)
            for r in data["rows"]:
                full_text += (
                    f"| {r[4]} | {r[5]} | {r[6]} | {r[7]} | {r[8]} | {r[9]} | {r[10]} | {r[11]} | {r[12]} |\n"
                )
            full_text += "\n\n"

    return full_text


def save_as_mobile_html(report_text, adset_id):
    html = markdown.markdown(report_text, extensions=['tables'])
    filename = f"adset_report_{adset_id}_mobile.html"

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Adset Report {adset_id}</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                    margin: 10px;
                    font-size: 14px;
                    line-height: 1.4;
                }}

                h3 {{
                    color: #333;
                    font-size: 16px;
                    margin-bottom: 10px;
                    word-wrap: break-word;
                }}

                table {{
                    border-collapse: collapse;
                    width: 100%;
                    font-size: 12px;
                    overflow-x: auto;
                    display: block;
                    white-space: nowrap;
                }}

                th, td {{
                    border: 1px solid #ddd;
                    padding: 4px 6px;
                    text-align: left;
                }}

                th {{
                    background-color: #f2f2f2;
                    font-weight: bold;
                    position: sticky;
                    top: 0;
                }}

                /* Мобильная версия таблицы */
                @media (max-width: 768px) {{
                    table {{
                        font-size: 10px;
                    }}

                    th, td {{
                        padding: 2px 4px;
                    }}

                    body {{
                        margin: 5px;
                    }}
                }}

                /* Горизонтальная прокрутка для таблицы */
                .table-container {{
                    overflow-x: auto;
                    -webkit-overflow-scrolling: touch;
                }}
            </style>
        </head>
        <body>
            <div class="table-container">
                {html}
            </div>
        </body>
        </html>
        """)
    return filename


def get_campaign_status(campaign_id):
    url = "https://graph.facebook.com/v23.0/act_1011840574303712/campaigns"
    params = {
        "fields": "id,name,status",
        "access_token": access_token,
        "filtering": f'["field": "campaign.id", "operator": "EQUAL", "value": {campaign_id}]'
    }
    resp = requests.get(url, params=params)
    data = resp.json()
    return data['data'][0]['status']


def get_metrics_for_day():
    additions = []
    url = "https://graph.facebook.com/v23.0/act_1011840574303712/insights"

    timestamp = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")

    params = {
        "level": "adset",
        "fields": "campaign_id,adset_id,campaign_name,adset_name,date_start,date_stop,"
                  "spend,impressions,clicks,ctr,cpm,actions",
        "access_token": access_token,
        "time_range[since]": timestamp,
        "time_range[until]": timestamp,
        "time_increment": 1,
        # "filtering": f'[{{"field": "campaign.id", "operator": "EQUAL", "value": {campaign_id}}}]'
    }
    resp = requests.get(url, params=params)
    data = resp.json()
    print(data)
    for row in data["data"]:
        if get_status(int(row["adset_id"])) == "ACTIVE":
            print(row["adset_id"])
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

            cr = round(int(leads) / clicks, 4) if clicks > 0 else 0
            cpl = round(spend / int(leads), 4) if int(leads) > 0 else 0
            ctr = round(clicks / impressions * 100, 4) if impressions > 0 else 0
            cpm = round(spend / impressions * 1000, 4) if impressions > 0 else 0

            timestamp = row['date_stop']
            params = (
                row["adset_id"],
                row['adset_name'],
                row["campaign_id"],
                timestamp,
                spend,
                impressions,
                clicks,
                leads,
                cr,
                cpl,
                ctr,
                cpm
            )
            db.insert_ad_metrics(params=params)
            additions.append({"adset_id": row['adset_id'], "adset_name": row['adset_name']})

    return additions

# get_metrics_for_day("2025-08-15")
# print(get_status(120215616952620753))


def get_status_from_meta():
    url = "https://graph.facebook.com/v23.0/act_1011840574303712/adsets"
    params = {
        "fields": "id,name,campaign_id,status,campaign{id,name}",
        "access_token": access_token,
        "filtering": '[{"field":"effective_status","operator":"IN","value":["ACTIVE"]}]'
    }
    resp = requests.get(url, params=params)
    data = resp.json()
    for row in data['data']:
        db.insert_into_status_table((row['campaign']['id'], row['campaign']['name'], row['id'],
                                     row['name'], row['status']))

# get_metrics_for_today("2025-08-05")
# get_status_from_meta()


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


def get_form_id_by_adset_id(adset_id):
    ads_url = f"https://graph.facebook.com/v23.0/{adset_id}/ads"
    ads_params = {
        "access_token": access_token,
        "fields": "id,name,creative"
    }
    ads_resp = requests.get(ads_url, params=ads_params)
    ads_data = ads_resp.json()['data']
    # print(ads_data)

    creative_id = ads_data[0]['creative']['id']
    if len(ads_data) > 1:
        creative_id = ads_data[1]['creative']['id']

    # print(creative_id)

    creative_url = f"https://graph.facebook.com/v23.0/{creative_id}"
    creative_params = {
        "access_token": access_token,
        "fields": "id,name,status,object_story_spec,call_to_action_type"
        # "fields": "status,effective_status,object_story_spec{video_data{call_to_action{value}}}"
    }
    creative_resp = requests.get(creative_url, params=creative_params).json()
    # print("resp_cre", creative_resp)
    form_id = creative_resp['object_story_spec']['video_data']['call_to_action']['value']['lead_gen_form_id']

    return form_id

# print(get_form_id_by_adset_id(120215616952620753))


def get_number_kval_leads(adset_id, target_date):

    lst_ad_ids = set()

    form_id = get_form_id_by_adset_id(adset_id)

    start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_next_day = start_of_day + timedelta(days=1)

    start_ts = int(start_of_day.timestamp())
    end_ts = int(start_of_next_day.timestamp()) - 1  # Исключаем следующий день

    # print(f"Точные границы: {start_ts} ({start_of_day}) - {end_ts} ({datetime.fromtimestamp(end_ts)})")

    filtering = [
        {"field": "time_created", "operator": "GREATER_THAN_OR_EQUAL", "value": start_ts},
        {"field": "time_created", "operator": "LESS_THAN", "value": end_ts}
    ]

    url = f'https://graph.facebook.com/v23.0/{form_id}/leads'
    params = {
        'access_token': access_token,
        'fields': 'id,created_time,ad_id,form_id,field_data,adset_id',
        'filtering': json.dumps(filtering)
    }

    response = requests.get(url, params=params)
    data = response.json()
    print('data', data)
    # Дополнительная проверка на клиенте
    filtered_leads = data['data']
    # for lead in data.get('data', []):
    #     created_time = lead.get('created_time')
    #     if created_time:
    #         lead_date = datetime.strptime(created_time, '%Y-%m-%dT%H:%M:%S%z')
    #         if lead_date.date() == target_date.date():
    #             filtered_leads.append(lead)

    # print(f"API вернул: {len(data.get('data', []))} лидов")
    # print(f"После фильтрации на клиенте: {len(filtered_leads)} лидов")
    print("leads ", filtered_leads)
    numbers = []
    counter = 0
    for lead in filtered_leads:
        number = lead['field_data'][5]["values"][0]
        numbers.append(number)
        counter += checking_kval(number)
        if checking_kval(number):
            print(number)

    print(f"lst: {len(numbers)}", numbers)
    print(f"set: {len(set(numbers))}", set(numbers))

    return counter


target_date = datetime(2025, 8, 5)
leads = get_number_kval_leads(120215614681850753, target_date)
# print("leads", leads)

# print(get_metrics_from_meta(120222881867660753))


# def count_kval_leads(leads):
#     counter = 0
#     for lead in leads:
#         number = lead['field_data'][5]["values"][0]
#         counter += checking_kval(number)
#         if checking_kval(number):
#             print(number)
#     return counter
#
#
# print(count_kval_leads(leads))


def get_metrics_from_meta(campaign_id):
    timestamp = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")

    url = (
        f"https://graph.facebook.com/v23.0/act_1011840574303712/insights"
        f"?level=adset"
        f"&fields=campaign_id,adset_id,campaign_name,adset_name,date_start,date_stop,"
        f"spend,impressions,clicks,ctr,cpm,actions"
        f"&access_token={access_token}&"
        f"time_range[since]=2025-08-12&time_range[until]=2025-08-19&time_increment=1"
        f"&filtering=[{{\"field\":\"campaign.id\",\"operator\":\"EQUAL\",\"value\":\"{campaign_id}\"}}]"
    )
    # print(date_since, timestamp)

    response = requests.get(url)
    data = response.json()
    lst = []
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

        cr = round(int(leads) / clicks, 4) if clicks > 0 else 0
        cpl = round(spend / int(leads), 4) if int(leads) > 0 else 0
        ctr = round(clicks / impressions * 100, 4) if impressions > 0 else 0
        cpm = round(spend / impressions * 1000, 4) if impressions > 0 else 0

        timestamp = row['date_stop'].split("-")
        year = int(timestamp[0])
        month = int(timestamp[1])
        day = int(timestamp[2])

        target_date = datetime(year, month, day)
        kval_leads = get_number_kval_leads(row['adset_id'], target_date)
        timestamp = row['date_stop']

        # lst.append(row["adset_id"])

        params = (
            row["adset_id"],
            row['adset_name'],
            row["campaign_id"],
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
        db.insert_ad_metrics(params=params)
    # print(set(lst))


# print(get_metrics_from_meta(120215614681840753))
# print((datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"))
