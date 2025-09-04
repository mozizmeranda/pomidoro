import requests
from config import *

headers = {
    "Authorization": f"Bearer {amocrm_access_token}",
    "Content-Type": "application/json"
}
# resp = requests.get(url, headers=headers, params=params)
# print(resp.json())

# payload = {
#     'client_id': amocrm_id,
#     'client_secret': amocrm_client_secret,
#     'grant_type': 'authorization_code',
#     'code': "def502009ef31a72d2bc955a1de1eba3b7181229a97fe2e4cdb87f4fc24bfc52a5a477d3db077d3f8954ea75c4bf10240f9cf2f0612220b478593f7ac188af5c1a3393a51705b2f258c9bd8ca273c37ff1c42469c98978c4c5db51437cce4fccb4bbf1b64adc38cce2fc192a849f6ca26bde901dc003fa6a8363c7b2f6c6b19961a27031659eb70ada80da713544939316bc2454aa590055911a65a836b03bf94c44e1080b942cbf280daca208ea10ffb082231d317c905c79db6a76ce776206af6d29e84a65c1cbf8855562c90f92a26146be29bcacf1e4e32baf6b31135a24c237245ae20461001b140a0be6459f2c03d613ff5a8cd576277a02038b7d977f5fdee960ad97774720e2d0f5e68b165659f192735b1d97963717209c5c59a19145f25485588382d6cdd216146e824fb4d9a65a42c537522725228a11562e3e0c4028a7c2f6c08385310a00876e1205298a5ddbba247faf38c5653bc12c93af559d5d3998cba923ae15017eb6a5a12b9fd610c10b456c5781df5e532f4b37d1840c24e1801b70e413286d4e82878fcb6dd7f2039d109c5f437a28cfd097752ee09b3e6bcaad9a0f86e1c900a70a2f23cf5afba4a39d23cea77e59b8495c2a931e3793f208d1dd1437ce7a43585b4d015c8fc0ffdacacbb1c17e60e85dd29f9d227d1b18ab8a9193759df8",
#     'redirect_uri': "https://www.youtube.com/"
# }
#
# headers = {
#     'Content-Type': 'application/json'
# }
# url = f'https://{amocrm_subdomain}.amocrm.ru/oauth2/access_token'
#
# response = requests.post(url, json=payload, headers=headers)
# print(response.status_code)
# print(response.json())


# def get_contact_deals(contact_id):
#     url = f'https://issouz.amocrm.ru/api/v4/contacts/{contact_id}'
#     params = {
#         'with': 'leads'  # Включить информацию о контактах
#     }
#     c_headers = {
#         'Authorization': f'Bearer {amocrm_access_token}',
#         'Content-Type': 'application/hal+json'
#     }
#
#     response = requests.get(url, headers=c_headers, params=params)
#     data = response.json()
#
#     if 'error' in data:
#         print(f"Ошибка получения сделок: {data['error']}")
#         return []
#
#     return data

def check_lead_id_with_pipeline_id(lead_id):
    url = f"https://issouz.amocrm.ru/api/v4/leads/{lead_id}"

    resp = requests.get(url, headers=headers)
    data = resp.json()
    print("data", data)
    if data['pipeline_id'] == 8388646:
        return 1

    return 0


def checking_kval(phone_number):
    contact_url = f'https://issouz.amocrm.ru/api/v4/contacts'
    contact_params = {
        'query': phone_number,  # amoCRM автоматически найдет по телефону
        'with': "leads"
    }

    response = requests.get(contact_url, headers=headers, params=contact_params)
    print("resp", response.content)
    # print(f"resp -- {phone_number} -- ", response.content)
    if not response.content:
        return -1
    data = response.json()
    # print(data)
    kval = 0

    for lead in data['_embedded']["contacts"][0]['_embedded']['leads']:
        lead_id = lead['id']
        if check_lead_id_with_pipeline_id(lead_id):
            return 1

    return 0


def get_pipelines_info():
    """Получить информацию о всех воронках и их этапах"""

    url = f'https://issouz.amocrm.ru/api/v4/leads/pipelines'
    headers = {
        'Authorization': f'Bearer {amocrm_access_token}',
        'Content-Type': 'application/json'
    }

    response = requests.get(url, headers=headers)
    data = response.json()

    if 'error' in data:
        print(f"Ошибка получения воронок: {data['error']}")
        return {}

    # Создаем словарь для быстрого поиска
    pipelines_dict = {}
    pipelines = data.get('_embedded', {}).get('pipelines', [])

    for pipeline in pipelines:
        pipeline_id = pipeline.get('id')
        pipeline_name = pipeline.get('name')

        statuses = {}
        for status in pipeline.get('_embedded', {}).get('statuses', []):
            status_id = status.get('id')
            status_name = status.get('name')
            statuses[status_id] = status_name

        pipelines_dict[pipeline_id] = {
            'name': pipeline_name,
            'statuses': statuses
        }

    return pipelines_dict


# print(get_pipelines_info())
