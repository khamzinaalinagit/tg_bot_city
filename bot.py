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


async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /settings — показать текущие настройки пользователя."""
    init_db()
    user_id = update.effective_user.id
    s = get_settings(user_id)
    await update.message.reply_text(
        "⚙️ Твои настройки:\n"
        f"• rating_type: {s['rating_type']}\n"
        f"• city_limit: {s['city_limit']}\n"
        f"• lang: {s['lang']}\n"
    )


async def cmd_set_limit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /set_limit N — сохранить лимит рейтинга в БД."""
    init_db()
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Использование: /set_limit 10")
        return

    try:
        n = int(context.args[0])
        if n < 5 or n > 50:
            await update.message.reply_text("Лимит должен быть от 5 до 50.")
            return
        set_limit(user_id, n)
        await update.message.reply_text(f"✅ Лимит установлен: {n}")
    except Exception:
        await update.message.reply_text("❌ Ошибка. Пример: /set_limit 10")


async def cmd_set_rating(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /set_rating population|temp — сохраняет тип рейтинга."""
    init_db()
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Использование: /set_rating population|temp")
        return

    rating = context.args[0].strip().lower()
    if rating not in {"population", "temp"}:
        await update.message.reply_text("Допустимо: population или temp")
        return

    set_rating_type(user_id, rating)
    await update.message.reply_text(f"✅ Тип рейтинга установлен: {rating}")


async def cmd_set_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /set_lang ru|en — сохраняет язык."""
    init_db()
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Использование: /set_lang ru|en")
        return

    lang = context.args[0].strip().lower()
    if lang not in {"ru", "en"}:
        await update.message.reply_text("Допустимо: ru или en")
        return

    set_lang(user_id, lang)
    await update.message.reply_text(f"✅ Язык установлен: {lang}")


async def _reply_weather_for_city(update: Update, context: ContextTypes.DEFAULT_TYPE, city: Dict[str, Any]) -> None:
    """Формируем ответ: справка по городу + температура (если доступно)."""
    geo = context.bot_data["geo"]
    weather = context.bot_data["weather"]

    # Иногда в find_city данных меньше — доберём детали по id (если есть)
    city_id = city.get("id")
    if city_id:
        try:
            details = await _get_city_details(geo, city_id)
            if details:
                city = {**city, **details}
        except Exception:
            pass

    info = _fmt_city_info(city)

    lat = city.get("latitude")
    lon = city.get("longitude")

    temp_txt = "🌡 Температура: нет данных (не задан OPENWEATHER_KEY)"
    if lat is not None and lon is not None:
        try:
            t = await _get_temp(weather, float(lat), float(lon))
            if t is None:
                temp_txt = "🌡 Температура: нет данных (не задан OPENWEATHER_KEY)"
            else:
                temp_txt = f"🌡 Температура сейчас: {t:.1f}°C"
        except Exception as exc:
            temp_txt = f"🌡 Температура: ошибка получения ({exc})"

    await update.message.reply_text(info + "\n\n" + temp_txt)


async def cmd_weather(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /weather <город>."""
    geo = context.bot_data["geo"]
    init_db()
    user_id = update.effective_user.id
    s = get_settings(user_id)

    if not context.args:
        await update.message.reply_text("Использование: /weather Москва")
        return

    name = " ".join(context.args).strip()
    if not name:
        await update.message.reply_text("Напиши название города после команды.")
        return

    candidates = await _get_city_candidates(geo, name, limit=5)
    if not candidates:
        await update.message.reply_text("Город не найден. Попробуй другое название.")
        return

    if len(candidates) == 1:
        await _reply_weather_for_city(update, context, candidates[0])
        return

    # Много вариантов — сохраним в user_data и попросим выбрать номер
    context.user_data["pending_cities"] = candidates
    lines = ["Нашла несколько городов. Ответь номером (1..5):"]
    for i, c in enumerate(candidates, start=1):
        lines.append(_fmt_city_line(i, c))
    await update.message.reply_text("\n".join(lines))


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Любой текст:
    - если ожидаем выбор номера (pending_cities) → принимаем номер
    - иначе считаем текст названием города и ищем
    """
    geo = context.bot_data["geo"]
    init_db()
    user_id = update.effective_user.id
    s = get_settings(user_id)

    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text("Напиши название города.")
        return

    # Если ждём выбор номера из списка
    pending = context.user_data.get("pending_cities")
    if pending:
        if text.isdigit():
            idx = int(text)
            if 1 <= idx <= len(pending):
                city = pending[idx - 1]
                context.user_data.pop("pending_cities", None)
                await _reply_weather_for_city(update, context, city)
                return

        await update.message.reply_text("Ответь числом из списка (например: 1).")
        return

    # Иначе текст — это название города
    candidates = await _get_city_candidates(geo, text, limit=5)
    if not candidates:
        await update.message.reply_text("Город не найден. Попробуй другое название.")
        return

    if len(candidates) == 1:
        await _reply_weather_for_city(update, context, candidates[0])
        return

    context.user_data["pending_cities"] = candidates
    lines = ["Нашла несколько городов. Ответь номером (1..5):"]
    for i, c in enumerate(candidates, start=1):
        lines.append(_fmt_city_line(i, c))
    await update.message.reply_text("\n".join(lines))


async def cmd_top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /top — показывает рейтинг городов (population или temp)."""
    init_db()
    user_id = update.effective_user.id
    s = get_settings(user_id)

    geo: GeoDBClient = context.bot_data["geo"]
    weather: WeatherClient = context.bot_data["weather"]

    limit = int(s["city_limit"])
    rating = s["rating_type"]

    await update.message.reply_text(f"⏳ Формирую рейтинг ({rating}), лимит {limit}...")

    # Берём топ городов по населению как базовый список
    try:
        cities = await _to_thread(geo.top_cities_by_population, limit, None)
    except Exception as exc:
        await update.message.reply_text(f"Ошибка GeoDB: {exc}")
        return

    if not cities:
        await update.message.reply_text("Не удалось получить список городов.")
        return

    if rating == "population":
        lines = ["🏆 ТОП городов по населению:"]
        for i, c in enumerate(cities, start=1):
            name = c.get("name", "Unknown")
            country = c.get("country", "")
            pop = c.get("population", "")
            lines.append(f"{i}. {name} ({country}) — {pop}")
        await update.message.reply_text("\n".join(lines))
        return

    if rating == "temp":
        # Считаем температуры и сортируем по ним
        scored = []
        for c in cities:
            lat = c.get("latitude")
            lon = c.get("longitude")
            if lat is None or lon is None:
                continue
            try:
                t = await _get_temp(weather, float(lat), float(lon))
                if t is None:
                    continue
                scored.append((t, c))
            except Exception:
                continue

        if not scored:
            await update.message.reply_text("Температуры недоступны (проверь OPENWEATHER_KEY).")
            return

        scored.sort(key=lambda x: x[0], reverse=True)
        lines = ["🌡 ТОП городов по температуре (сейчас):"]
        for i, (t, c) in enumerate(scored[:limit], start=1):
            name = c.get("name", "Unknown")
            country = c.get("country", "")
            lines.append(f"{i}. {name} ({country}) — {t:.1f}°C")
        await update.message.reply_text("\n".join(lines))
        return

    await update.message.reply_text("Неизвестный тип рейтинга. Используй /set_rating population|temp")


def main() -> None:
    if not TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN не задан. Создай .env и добавь TELEGRAM_TOKEN=...")

    init_db()

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Инициализируем клиентов и кладём их в bot_data, чтобы не создавать на каждый запрос
    app.bot_data["geo"] = GeoDBClient()
    app.bot_data["weather"] = WeatherClient()

    # Команды
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("settings", cmd_settings))
    app.add_handler(CommandHandler("set_limit", cmd_set_limit))
    app.add_handler(CommandHandler("set_rating", cmd_set_rating))
    app.add_handler(CommandHandler("set_lang", cmd_set_lang))
    app.add_handler(CommandHandler("weather", cmd_weather))
    app.add_handler(CommandHandler("top", cmd_top))

    # Любой текст (название города / выбор номера)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    # Запуск
    app.run_polling(close_loop=False)


if __name__ == "__main__":
    main()
