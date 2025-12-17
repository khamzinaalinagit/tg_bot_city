import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "").strip()
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "").strip()
OPENWEATHER_KEY = os.getenv("OPENWEATHER_KEY", "").strip()

DB_PATH = os.getenv("DB_PATH", "bot.sqlite3")
DEFAULT_LIMIT = int(os.getenv("DEFAULT_LIMIT", "10"))
DEFAULT_RATING = os.getenv("DEFAULT_RATING", "population")
DEFAULT_LANG = os.getenv("DEFAULT_LANG", "ru")

