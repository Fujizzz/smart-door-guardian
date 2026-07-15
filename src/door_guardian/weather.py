"""Weather lookup using the key-free Open-Meteo API."""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.request import urlopen

from .config import Settings


WEATHER_CODES = {
    0: "晴朗",
    1: "大部晴朗",
    2: "局部多云",
    3: "阴天",
    45: "雾",
    48: "雾凇",
    51: "小毛毛雨",
    53: "毛毛雨",
    55: "强毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    80: "小阵雨",
    81: "阵雨",
    82: "强阵雨",
    95: "雷雨",
}


@dataclass(frozen=True)
class WeatherSnapshot:
    temperature_c: float
    wind_speed_kmh: float
    description: str

    def sentence(self) -> str:
        return (
            f"当前天气{self.description}，气温 {self.temperature_c:.1f} 摄氏度，"
            f"风速 {self.wind_speed_kmh:.1f} 公里每小时。"
        )


class WeatherService:
    endpoint = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def current(self, timeout: float = 8.0) -> WeatherSnapshot:
        query = urlencode(
            {
                "latitude": self.settings.weather_latitude,
                "longitude": self.settings.weather_longitude,
                "current": "temperature_2m,weather_code,wind_speed_10m",
                "timezone": self.settings.weather_timezone,
            }
        )
        with urlopen(f"{self.endpoint}?{query}", timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        current = payload["current"]
        code = int(current["weather_code"])
        return WeatherSnapshot(
            temperature_c=float(current["temperature_2m"]),
            wind_speed_kmh=float(current["wind_speed_10m"]),
            description=WEATHER_CODES.get(code, f"天气代码 {code}"),
        )

