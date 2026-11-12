"""Web tools: open sites, search, Wikipedia and weather (no API keys needed)."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
import webbrowser

USER_AGENT = "VisionAssistant/1.0 (https://github.com/Kaarthik33/vision)"

WEATHER_CODES = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "freezing fog", 51: "light drizzle", 53: "drizzle",
    55: "heavy drizzle", 61: "light rain", 63: "rain", 65: "heavy rain",
    71: "light snow", 73: "snow", 75: "heavy snow", 80: "rain showers",
    81: "rain showers", 82: "violent rain showers", 95: "thunderstorm",
    96: "thunderstorm with hail", 99: "thunderstorm with heavy hail",
}


def get_json(url: str, params: dict | None = None, timeout: int = 15) -> dict:
    if params:
        url += "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def open_website(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    webbrowser.open(url)
    return f"Opened {url} in the browser."


def web_search(query: str) -> str:
    webbrowser.open("https://duckduckgo.com/?" + urllib.parse.urlencode({"q": query}))
    return f"Opened a web search for '{query}' in the browser."


def wikipedia(topic: str) -> str:
    found = get_json(
        "https://en.wikipedia.org/w/api.php",
        {"action": "query", "list": "search", "srsearch": topic, "srlimit": 1, "format": "json"},
    )
    hits = found.get("query", {}).get("search", [])
    if not hits:
        return f"No Wikipedia article found for '{topic}'."
    title = hits[0]["title"]
    summary = get_json(
        "https://en.wikipedia.org/api/rest_v1/page/summary/"
        + urllib.parse.quote(title.replace(" ", "_"), safe="")
    )
    return f"{title}: {summary.get('extract', 'No summary available.')}"


def weather(city: str) -> str:
    places = get_json(
        "https://geocoding-api.open-meteo.com/v1/search", {"name": city, "count": 1}
    ).get("results")
    if not places:
        return f"Could not find a place called '{city}'."
    place = places[0]
    now = get_json(
        "https://api.open-meteo.com/v1/forecast",
        {
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,"
                       "wind_speed_10m,weather_code",
        },
    )["current"]
    sky = WEATHER_CODES.get(now.get("weather_code"), "unknown conditions")
    return (
        f"{place['name']}, {place.get('country', '')}: {sky}, "
        f"{now['temperature_2m']}°C (feels like {now['apparent_temperature']}°C), "
        f"humidity {now['relative_humidity_2m']}%, wind {now['wind_speed_10m']} km/h."
    )


def register(registry) -> None:
    registry.register(
        "open_website", "Open a website in the default browser.",
        {"url": {"type": "string"}}, ["url"],
    )(open_website)
    registry.register(
        "web_search", "Open a web search for a query in the default browser.",
        {"query": {"type": "string"}}, ["query"],
    )(web_search)
    registry.register(
        "wikipedia", "Look up a topic on Wikipedia and return a short summary.",
        {"topic": {"type": "string"}}, ["topic"],
    )(wikipedia)
    registry.register(
        "weather", "Get the current weather for a city.",
        {"city": {"type": "string"}}, ["city"],
    )(weather)
