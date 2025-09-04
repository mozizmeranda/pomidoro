from aiogram import types, Dispatcher, Bot
import asyncio
from aiogram.types import FSInputFile, BotCommand
from config import bot_token, hour, minute
from aiogram.filters import Command
import re
from llm import gpt_v2
from api_meta_ads import save_as_mobile_html
from meta_api import _active_adsets, get_metrics_for_day, get_metrics_from_db
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import requests
from database import *


bot = Bot(token=bot_token)
dp = Dispatcher()
scheduler = AsyncIOScheduler()


def format_for_telegram(text):
    """Форматирует текст для лучшего отображения в Telegram"""

    # Заменяем заголовки на жирный текст
    text = re.sub(r'##\s*(.*)', r'*\1*', text)  # ## Заголовок -> *Заголовок*
    text = re.sub(r'#\s*(.*)', r'**\1**', text)  # # Заголовок -> **Заголовок**

    # Заменяем списки на эмодзи
    text = re.sub(r'^\d+\.\s*', '🔸 ', text, flags=re.MULTILINE)
    text = re.sub(r'^\*\s*', '• ', text, flags=re.MULTILINE)
    text = re.sub(r'^-\s*', '• ', text, flags=re.MULTILINE)

    # Добавляем разделители
    # text = re.sub(r'\n\n', '\n━━━━━━━━━━━━━━━\n', text)

    return text


prompt_for_auto_check = """Это автоматическое сообщение. Без моего одобрения ничего не предпринимать!
Твоя задача проанализировать метрики, в метриках я также добавил новые свежие метрики. 

Сделай анализ и верни свой фидбек, свои рекомендации. 
Пока не вызывай никаких функций, просто верни свои рекомендации по изменениям.
Только после моего одобрение можно будет вызвать функция по перераспределению бюджета или по 
отключению неэффективных групп объявлений.
Ниже я напишу метрики по всем креативам."""


async def scheduled_analysis():
    chat_id = 6287458105
    active_adsets = _active_adsets()  # list()
    get_metrics_for_day()  # getting fresh auto metrics and inserting them into db
    request_text = ""
    for adset in active_adsets:
        # request_text += f"### Campaign name = {adset['name']}\n Campaign ID = {adset['id']}\n\n"
        request_text += get_metrics_from_db(adset['id'])
        request_text += "\n\n---\n\n\n"
    # print(request_text)
    full_text = prompt_for_auto_check + "\n\n" + request_text
    filename = save_as_mobile_html(full_text, 123)
    doc = FSInputFile(filename, "adset_report_123_mobile.html")
    await bot.send_document(
        chat_id=chat_id,
        document=doc,
        caption=f"📊 Отчет"
    )
    r = gpt_v2(full_text)
    paragraphs = r.split("---")
    for i in paragraphs:
        await bot.send_message(chat_id=chat_id, text=format_for_telegram(i))


requests.get(f"https://api.telegram.org/bot{bot_token}/sendMessage?"
             f"chat_id=6287458105&text=123")

# asyncio.run(scheduled_analysis())


@dp.message(Command("start"))
async def start(message: types.Message):
    await message.reply("Привет, я AI таргетолог.")


async def set_commands():
    commands = [
        BotCommand(command="start", description="Запуск бота"),
        BotCommand(command="campaigns", description="Чтобы получить все доступные кампании."),
        BotCommand(command="gpt", description="Запрос к GPT"),
        BotCommand(command="analyze", description="Анализ кампании"),
    ]
    await bot.set_my_commands(commands)


@dp.message(Command("gpt"))
async def gpt_request(message: types.Message):
    t = message.text

    if t.startswith("/gpt "):
        extracted_text = t[5:]
        await message.reply(f"You asked: {extracted_text}")
        r = gpt_v2(extracted_text)
        paragraphs = r.split("---")

        for i in paragraphs:
            await message.answer(text=format_for_telegram(i))

    else:
        pass


@dp.message(Command("analyze"))
async def get_creatives(message: types.Message):
    parts = message.text.strip().split(maxsplit=2)
    if len(parts) < 2:
        await message.reply("❗Формат: /analyze CAMPAIGN_ID \n\n[ваш текст]")
        return

    campaign_id = parts[1]
    extracted_text = parts[2] if len(parts) > 2 else ""

    metrics = get_metrics_from_db(campaign_id)
    full_text = f"{extracted_text}\n\n{metrics}"
    filename = save_as_mobile_html(metrics, 123)
    doc = FSInputFile(filename, "adset_report_123_mobile.html")
    await bot.send_document(
        chat_id=message.from_user.id,
        document=doc,
        caption=f"📊 Отчет"
    )
    r = gpt_v2(full_text)
    paragraphs = r.split("---")
    for i in paragraphs:
        await message.answer(text=format_for_telegram(i))


@dp.message(Command("text"))
async def get_creatives(message: types.Message):
    parts = message.text.strip().split(maxsplit=2)
    if len(parts) < 2:
        await message.reply("❗ Формат: /analyze CAMPAIGN_ID [ваш текст]")
        return

    campaign_id = parts[1]
    user_text = parts[2] if len(parts) > 2 else ""
    await message.reply(f"{campaign_id} -- {user_text}")


@dp.message(Command("campaigns"))
async def send_campaigns(message: types.Message):
    campaigns = db.get_campaigns()
    ans = ""
    ids = []
    for i in campaigns:
        if i[0] not in ids:
            ans += f"Name = {i[1]} -- ID = <code>{i[0]}</code>\n\n"
            ids.append(i[0])

    await message.reply(ans, parse_mode="HTML")


async def main():
    scheduler.add_job(scheduled_analysis, 'cron', hour=16, minute=30)

    scheduler.start()
    await set_commands()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
