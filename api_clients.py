from typing import Dict, List, Optional, Tuple
import requests
from config import RAPIDAPI_KEY, RAPIDAPI_HOST, OPENWEATHER_KEY


class GeoDBClient:
    BASE = "https://wft-geo-db.p.rapidapi.com/v1/geo"

    def __init__(self):
        if not RAPIDAPI_KEY:
            raise RuntimeError("RAPIDAPI_KEY не задан в .env")
        self.headers = {
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            "X-RapidAPI-Host": RAPIDAPI_HOST,
        }
