from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "TravelWeatherMCP",
    stateless_http=True,
    streamable_http_path="/",
)

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def weather_code_to_text(code: int | None) -> str:
    mapping = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Rime fog",
        51: "Light drizzle",
        61: "Rain",
        71: "Snow",
        95: "Thunderstorm",
    }
    return mapping.get(code, "Unknown")


async def geocode_city(city: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(GEOCODE_URL, params={"name": city, "count": 1})
        response.raise_for_status()
        data = response.json()

    results = data.get("results", [])
    if not results:
        raise ValueError(f"Could not find city '{city}'")

    place = results[0]
    return {
        "name": place.get("name"),
        "country": place.get("country"),
        "latitude": place.get("latitude"),
        "longitude": place.get("longitude"),
    }


async def fetch_weather(latitude: float, longitude: float, days: int = 3) -> dict[str, Any]:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min",
        "forecast_days": days,
        "timezone": "auto",
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(FORECAST_URL, params=params)
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_current_weather(city: str) -> dict[str, Any]:
    """Get the current weather for a city."""
    place = await geocode_city(city)
    weather = await fetch_weather(place["latitude"], place["longitude"], days=1)

    current = weather.get("current", {})
    weather_text = weather_code_to_text(current.get("weather_code"))

    return {
        "city": place["name"],
        "country": place["country"],
        "current_weather": {
            "temperature_c": current.get("temperature_2m"),
            "feels_like_c": current.get("apparent_temperature"),
            "humidity_percent": current.get("relative_humidity_2m"),
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "weather_code": current.get("weather_code"),
            "weather_text": weather_text,
        },
    }


@mcp.tool()
async def get_weather_forecast(city: str, days: int = 3) -> dict[str, Any]:
    """Get a short weather forecast for a city."""
    if days < 1:
        days = 1
    if days > 7:
        days = 7

    place = await geocode_city(city)
    weather = await fetch_weather(place["latitude"], place["longitude"], days=days)

    daily = weather.get("daily", {})
    times = daily.get("time", [])
    max_temps = daily.get("temperature_2m_max", [])
    min_temps = daily.get("temperature_2m_min", [])
    codes = daily.get("weather_code", [])

    forecast = []
    for i in range(len(times)):
        forecast.append(
            {
                "date": times[i],
                "max_temp_c": max_temps[i] if i < len(max_temps) else None,
                "min_temp_c": min_temps[i] if i < len(min_temps) else None,
                "weather_code": codes[i] if i < len(codes) else None,
                "weather_text": weather_code_to_text(codes[i] if i < len(codes) else None),
            }
        )

    return {
        "city": place["name"],
        "country": place["country"],
        "forecast_days": days,
        "forecast": forecast,
    }