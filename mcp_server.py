from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("TravelWeatherMCP", stateless_http=True)

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
        resp = await client.get(
            GEOCODE_URL,
            params={"name": city, "count": 1}
        )
        resp.raise_for_status()
        data = resp.json()

    results = data.get("results", [])
    if not results:
        raise ValueError(f"City not found: {city}")

    place = results[0]

    return {
        "city": place["name"],
        "country": place["country"],
        "latitude": place["latitude"],
        "longitude": place["longitude"],
    }


async def fetch_weather(lat: float, lon: float) -> dict[str, Any]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,wind_speed_10m,weather_code",
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(FORECAST_URL, params=params)
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
async def get_current_weather(city: str) -> dict:
    """Get current weather for a city."""
    place = await geocode_city(city)
    weather = await fetch_weather(place["latitude"], place["longitude"])

    current = weather.get("current", {})

    return {
        "city": place["city"],
        "country": place["country"],
        "temperature_c": current.get("temperature_2m"),
        "wind_kmh": current.get("wind_speed_10m"),
        "condition": weather_code_to_text(current.get("weather_code")),
    }


@mcp.tool()
async def get_trip_weather(from_city: str, to_city: str) -> dict:
    """Compare weather between two cities."""
    origin = await get_current_weather(from_city)
    destination = await get_current_weather(to_city)

    return {
        "from": origin,
        "to": destination,
        "summary": f"{from_city} is {origin['temperature_c']}°C, {to_city} is {destination['temperature_c']}°C"
    }