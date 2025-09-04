import requests
from io import BytesIO

token = "7605174176:AAFJrp7vgIHg5UAJMq7Niz7e4bWMkmyJHDo"


def send_mediagroup_photo(text):
    with open("link.txt", "r", encoding="utf-8") as f:
        images = [line.strip() for line in f if line.strip()]

    url = f"https://api.telegram.org/bot{token}/sendMediaGroup"
    media_group = []
    for idx, img in enumerate(images):
        if idx == 0:
            media_group.append({
                "type": "photo",
                "media": img,
                "caption": text,
                "parse_mode": "HTML"
            })
        else:
            media_group.append({
                "type": "photo",
                "media": img
            })
    json_data = {'chat_id': 6287458105, "media": media_group, "parse_mode": "HTML"}
    requests.get(url=url, json=json_data)


def send_mediagroup_video(text):
    with open("link.txt", "r", encoding="utf-8") as f:
        images = [line.strip() for line in f if line.strip()]

    url = f"https://api.telegram.org/bot{token}/sendMediaGroup"
    media_group = []
    for idx, vid in enumerate(images):
        if idx == 0:
            media_group.append({
                "type": "video",
                "media": vid,
                "caption": text,
                "parse_mode": "HTML"
            })
        else:
            media_group.append({
                "type": "video",
                "media": vid
            })
    json_data = {'chat_id': 6287458105, "media": media_group, "parse_mode": "HTML"}
    res = requests.get(url=url, json=json_data)
    print(res.content)


def get_image(image, text):
    data = {'chat_id': 6287458105, 'photo': image, 'caption': text}
    url = f"https://api.telegram.org/bot7605174176:AAFJrp7vgIHg5UAJMq7Niz7e4bWMkmyJHDo/sendPhoto"
    requests.get(url, params=data)


def get_video(video, text):
    # files = {'video': ('video.mp4', video)}
    data = {'chat_id': 6287458105, 'video': video, 'caption': text}
    url = f"https://api.telegram.org/bot7605174176:AAFJrp7vgIHg5UAJMq7Niz7e4bWMkmyJHDo/sendVideo"
    requests.get(url, params=data)


with open("link.txt", "r", encoding="utf-8") as f:
    content = f.read()

with open("text.txt", 'r', encoding="utf-8") as f:
    text = f.read()
#
# get_image(content, text)

# send_mediagroup_photo(text)
send_mediagroup_video(text)
# get_video(video=content, text=text)
