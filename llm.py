import requests
from config import open_ai_token
import json
from api_meta_ads import (llm_create_campaign, llm_create_adset, get_interests, update_adset_budget, set_adset_status,
                          get_adset_name_by_id)
from database import db
# openai_api_key = open_ai_token
from collections import defaultdict


headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {open_ai_token}"
}


with open("prompt.txt", 'r', encoding="utf-8") as f:
    p = f.read()


history = [
    {"role": "system", "content": p},
]


def get_chat():
    chat = db.get_chat()
    his = list()
    his.append({"role": "system", "content": p})
    for i in chat:
        if i[1] == "function":
            function_name = i[2]
            content = i[3]
            his.append({
                    "role": "function",
                    "name": function_name,
                    "content": content
                })
        else:
            role = i[1]
            content = i[3]
            his.append({"role": role, "content": content})
    return his


tools = [
    {
        "type": "function",
        "function": {
            "name": "create_campaign",
            "description": "Создать кампанию для Meta Ads.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Название кампании в Meta Ads"
                    },
                    "daily_budget": {
                        "type": "integer",
                        "description": "Дневной бюджет кампании в центах (не переводить в доллары)"
                    }
                },
                "required": ["name", "daily_budget"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_adset",
            "description": "Создать ad set для кампании Meta Ads",
            "parameters": {
                "type": "object",
                "properties": {
                    "campaign_id": {
                        "type": "integer",
                        "description": "ID кампании Meta Ads"
                    },
                    "audience_id": {
                        "type": "integer",
                        "description": "ID сохранённой аудитории (Saved Audience)"
                    },
                    "name": {
                        "type": "string",
                        "description": "Название для группы объявлений"
                    }
                },
                "required": ["campaign_id", "audience_id", "name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_adset_budget",
            "description": "Изменить бюджет группы объявлений по её ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "adset_id": {
                        "type": "integer",
                        "description": "ID группы объявлений"
                    },
                    "budget": {
                        "type": "integer",
                        "description": "Новый бюджет в центах. Максимум может быть 400"
                    },
                },
                "required": ["adset_id", "budget"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "change_status",
            "description": "Отключить неэффективную группу объявлений по её ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "adset_id": {
                        "type": "integer",
                        "description": "ID группы объявлений"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["PAUSED", "ACTIVE"],
                        "description": "Новый статус группы объявлений (PAUSED для отключения)"
                    }
                },
                "required": ["adset_id", "status"]
            }
        }
    }
]

token = "7605174176:AAEdzUKDE0bYrMWv-NA7HQaw3T6hQZXLll0"
chat_id = -1002695927579


def gpt_v2(text):
    history.append({"role": "user", "content": text})
    db.insert_into("user", text)
    his = get_chat()
    body = {
        "model": "gpt-4.1",
        "messages": his,
        "tools": tools,
        "tool_choice": "auto"
    }
    url = "https://api.openai.com/v1/chat/completions"
    response = requests.post(url, headers=headers, json=body)
    data = response.json()
    # print(data)
    message = data["choices"][0]["message"]

    if "tool_calls" in message:
        for tool_call in message["tool_calls"]:
            function_name = tool_call["function"]["name"]
            args = json.loads(tool_call["function"]["arguments"])

            # create_campaign. Для создания кампаний
            if function_name == "create_campaign":
                # print(f"Name: {args['name']} and budget: {args['daily_budget']}")
                d = llm_create_campaign(
                    name=args["name"],
                    daily_budget=args["daily_budget"]
                )
                requests.get(f"https://api.telegram.org/bot{token}/sendMessage?"
                             f"chat_id={chat_id}&text={d}")
                content = f"Создана кампания: {args['name']}, бюджет: {args['daily_budget']}\nОтвет: {d}"
                history.append({
                    "role": "function",
                    "name": function_name,
                    "content": content
                })
                db.insert_into_with_func("function", function_name, content)

            # create_adset. Для создания Групп объявлений.
            elif function_name == "create_adset":
                # print(f"Creating ad set with campaign_id: {args['campaign_id']}, audience_id: {args['audience_id']}")
                result = llm_create_adset(
                    name=args['name'],
                    campaign_id=args["campaign_id"],
                    audience_id=args["audience_id"]
                )
                requests.get(f"https://api.telegram.org/bot{token}/sendMessage?"
                             f"chat_id={chat_id}&text={result}")
                content = (f"Создан ad set для кампании {args['campaign_id']} с аудиторией {args['audience_id']}\n"
                           f"Ответ: {result}")
                history.append({
                    "role": "function",
                    "name": function_name,
                    "content": content
                })
                db.insert_into_with_func("function", function_name, content)

        # Для обновления бюджета группы объявления.
            elif function_name == "update_adset_budget":
                new_budget = args['budget']
                adset_id = args['adset_id']
                adset_info = get_adset_name_by_id(adset_id)
                resp = update_adset_budget(adset_id, new_budget)
                if resp['success'] is True:
                    content = (f"Бюджет {adset_info['name']} был изменен с {int(adset_info['daily_budget'])/100}$ на "
                               f"{args['budget']}")
                    # print(content)
                    db.insert_into_with_func("function", function_name, content)

            # Для выключения неэффективных групп объявлений
            elif function_name == "change_status":
                status = args['status']
                adset_id = args['adset_id']
                adset_info = get_adset_name_by_id(adset_id)
                resp = set_adset_status(adset_id, "PAUSED")
                content = f"Группа объявлений {adset_info['name']} была выключена."
                # print(content)
                db.insert_into_with_func("function", function_name, content)

        his = get_chat()
        followup_body = {
            "model": "gpt-4.1",
            "messages": his
        }
        followup_response = requests.post(url, headers=headers, json=followup_body)
        db.insert_into("assistant", followup_response.json()["choices"][0]["message"]["content"])
        # print("follow up: ", followup_response)
        return followup_response.json()["choices"][0]["message"]["content"]

    # Ответ без вызова функции
    history.append({"role": "assistant", "content": message["content"]})
    db.insert_into("assistant", message["content"])
    return message["content"]


# def analyze_metrics():
#     metrics = db.get_metrics()
#
#     # grouped[adset_id] = {"name": adset_name, "rows": [..]}
#     grouped = defaultdict(lambda: {"name": "", "rows": []})
#     for row in metrics:
#         adset_id = row[1]
#         adset_name = row[2]
#         grouped[adset_id]["name"] = adset_name
#         grouped[adset_id]["rows"].append(row)
#
#     full_text = ""
#     for adset_id, data in grouped.items():
#         body = get_interests(int(adset_id))
#         full_text += (f"### Adset ID: {adset_id} — {data['name']}.\n Интересы: {body['interests']}. "
#                       f"Daily_budget: {body['daily_budget']} центов.\n\n")
#         full_text += "| Date | Потрачено, $ | Impressions | Clicks | Leads | CR | CPL | CTR | CPM |\n"
#         full_text += "| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
#
#         # r: (id, adset_id, adset_name, campaign_id, timestamp, spend, impressions, clicks, leads, cr, cpl, ctr, cpm)
#         for r in data["rows"]:
#             full_text += (
#                 f"| {r[4]} | {r[5]} | {r[6]} | {r[7]} | {r[8]} | {r[9]} | {r[10]} | {r[11]} | {r[12]} |\n"
#             )
#         full_text += "\n\n"
#
#     return full_text


# print(analyze_metrics())
