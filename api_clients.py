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

    def find_city(self, name: str, limit: int = 5) -> List[Dict]:
        params = {"namePrefix": name, "limit": limit, "sort": "-population"}
        r = requests.get(f"{self.BASE}/cities", headers=self.headers, params=params, timeout=20)
        r.raise_for_status()
        return r.json().get("data", [])