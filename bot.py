import asyncio
from typing import Any, Dict, List, Optional

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from api_clients import GeoDBClient, WeatherClient
from config import TELEGRAM_TOKEN
from db import init_db, get_settings, set_limit, set_lang, set_rating_type


def _fmt_city_line(i: int, city: Dict[str, Any]) -> str:
    """Формирует одну строку для списка вариантов городов (когда найдено несколько)."""
    name = city.get("name", "Unknown")
    country = city.get("country", "")
    region = city.get("region", "")
    pop = city.get("population")
    pop_txt = f", pop={pop}" if pop else ""
    extra = ", ".join([x for x in [region, country] if x])
    extra_txt = f" ({extra})" if extra else ""
    return f"{i}. {name}{extra_txt}{pop_txt}"


def _fmt_city_info(city: Dict[str, Any]) -> str:
    """Короткая справка о городе."""
    name = city.get("name", "Unknown")
    country = city.get("country", "")
    region = city.get("region", "")
    pop = city.get("population")
    lat = city.get("latitude")
    lon = city.get("longitude")

    parts = [f"🏙 Город: {name}"]
    if region:
        parts.append(f"📍 Регион: {region}")
    if country:
        parts.append(f"🌍 Страна: {country}")
    if pop:
        parts.append(f"👥 Население: {pop}")
    if lat is not None and lon is not None:
        parts.append(f"🧭 Координаты: {lat}, {lon}")
    return "\n".join(parts)


async def _to_thread(func, *args, **kwargs):
    """Запускает блокирующую функцию (requests) в отдельном потоке, чтобы не подвешивать бота."""
    return await asyncio.to_thread(func, *args, **kwargs)


async def _get_city_candidates(geo: GeoDBClient, name: str, limit: int) -> List[Dict[str, Any]]:
    """Ищем город по имени через GeoDB (RapidAPI)."""
    return await _to_thread(geo.find_city, name, limit)


async def _get_city_details(geo: GeoDBClient, city_id: str) -> Dict[str, Any]:
    """Запрашиваем детальную информацию о городе."""
    return await _to_thread(geo.city_details, city_id)


async def _get_temp(weather: WeatherClient, lat: float, lon: float) -> Optional[float]:
    """Температура из OpenWeather (если ключ задан)."""
    return await _to_thread(weather.temp_celsius, lat, lon)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /start — приветствие и краткая инструкция."""
    init_db()
    if update.effective_user:
        _ = get_settings(update.effective_user.id)  # создаём/читаем настройки

    text = (
        "Привет! Я бот погоды 🌤\n\n"
        "Как пользоваться:\n"
        "• Просто напиши название города (например: Москва)\n"
        "• Или командой: /weather Москва\n\n"
        "Дополнительно:\n"
        "• /top — рейтинг городов (по настройке)\n"
        "• /settings — твои настройки\n"
        "• /set_limit 5..50 — сколько городов в рейтинге\n"
        "• /set_rating population|temp — тип рейтинга\n"
        "• /set_lang ru|en — язык (пока влияет только на настройки)\n"
    )
    await update.message.reply_text(text)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /help — список команд."""
    text = (
        "Команды:\n"
        "/start — старт\n"
        "/help — помощь\n"
        "/weather <город> — погода по городу\n"
        "/top — рейтинг городов\n"
        "/settings — показать настройки\n"
        "/set_limit <число> — лимит рейтинга (5..50)\n"
        "/set_rating population|temp — тип рейтинга\n"
        "/set_lang ru|en — язык\n"
    )
    await update.message.reply_text(text)
