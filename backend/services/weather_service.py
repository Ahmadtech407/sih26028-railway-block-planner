"""
Weather Service for Railway Track Operations & Maintenance Scheduling.

Provides real-time and forecasted meteorological parameters:
- Temperature (°C)
- Precipitation Probability (%) & Rainfall Intensity (mm/h)
- Wind Speed (km/h) & Atmospheric Visibility (km)
- Operational Weather Risk Classification (LOW / MEDIUM / HIGH / EXTREME)

Integrates with Open-Meteo API (free/open public meteorological service)
with a deterministic, calibrated simulated fallback provider.
"""

import os
import math
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple

import requests
from backend.schemas.api_models import SectionWeather, WeatherRiskEnum

# Coordinates mapping for railway divisions & major stations
SECTION_COORDINATES: Dict[str, Tuple[float, float, str]] = {
    "KNP-PRYJ-SEC-B": (26.4499, 80.3319, "Kanpur Central - Prayagraj"),
    "KNP-PRYJ-SEC-A": (26.4499, 80.3319, "Kanpur Central - Prayagraj"),
    "LKO-KNP-SEC-A": (26.8322, 80.9238, "Lucknow Charbagh - Kanpur"),
    "NDLS-CNB-SEC-A": (28.6431, 77.2197, "New Delhi - Kanpur Central"),
    "PRYJ-DDU-SEC-A": (25.4483, 81.8331, "Prayagraj - Pt. Deen Dayal Upadhyaya"),
}
DEFAULT_COORDINATES: Tuple[float, float, str] = (26.4499, 80.3319, "Kanpur Central - Prayagraj")

# In-memory TTL cache for meteorological queries to eliminate external API latency
_WEATHER_CACHE: Dict[str, Dict[str, Any]] = {}
WEATHER_CACHE_TTL_SECONDS = 300  # 5 minutes


def get_weather_cache_stats() -> Dict[str, Any]:
    """Returns telemetry and health statistics for the in-memory weather cache."""
    return {
        "cached_entries": len(_WEATHER_CACHE),
        "ttl_seconds": WEATHER_CACHE_TTL_SECONDS,
        "status": "OPERATIONAL",
    }

# Standard WMO Weather Interpretation Codes (WW)
WMO_WEATHER_MAP: Dict[int, Tuple[str, str]] = {
    0: ("Clear sky", "☀️"),
    1: ("Mainly clear", "🌤️"),
    2: ("Partly cloudy", "⛅"),
    3: ("Overcast", "☁️"),
    45: ("Fog", "🌫️"),
    48: ("Depositing rime fog", "🌫️"),
    51: ("Light drizzle", "🌦️"),
    53: ("Moderate drizzle", "🌦️"),
    55: ("Dense drizzle", "🌧️"),
    56: ("Light freezing drizzle", "🌧️"),
    57: ("Dense freezing drizzle", "🌧️"),
    61: ("Slight rain", "🌧️"),
    63: ("Moderate rain", "🌧️"),
    65: ("Heavy rain", "🌧️"),
    66: ("Light freezing rain", "🌧️"),
    67: ("Heavy freezing rain", "🌧️"),
    71: ("Slight snow fall", "🌨️"),
    73: ("Moderate snow fall", "🌨️"),
    75: ("Heavy snow fall", "🌨️"),
    77: ("Snow grains", "🌨️"),
    80: ("Slight rain showers", "🌦️"),
    81: ("Moderate rain showers", "🌧️"),
    82: ("Violent rain showers", "⛈️"),
    85: ("Slight snow showers", "🌨️"),
    86: ("Heavy snow showers", "🌨️"),
    95: ("Thunderstorm", "⛈️"),
    96: ("Thunderstorm with slight hail", "⛈️"),
    99: ("Thunderstorm with heavy hail", "⛈️"),
}


def calculate_weather_risk_score(
    rain_prob: int,
    rain_intensity: float,
    wind_speed: float,
    visibility_km: float,
    work_type: str = "Rail Replacement",
) -> Tuple[WeatherRiskEnum, int, str]:
    """
    Computes a mathematical hazard score (0-100) and risk category for track maintenance.
    Rail welding and OHE electrical maintenance have strict safety thresholds for rain and wind.
    """
    # Raw composite score
    vis_penalty = max(0.0, (10.0 - visibility_km) * 3.5)
    raw_score = (rain_prob * 0.35) + (rain_intensity * 4.5) + (wind_speed * 0.35) + vis_penalty
    score = int(max(0, min(100, round(raw_score))))

    # Work-type sensitivity multiplier
    is_electrical = "ohe" in work_type.lower() or "signal" in work_type.lower()
    is_welding = "rail" in work_type.lower() or "sleeper" in work_type.lower()

    if rain_intensity >= 15.0 or wind_speed >= 60.0 or visibility_km <= 0.5 or (is_electrical and rain_intensity >= 5.0):
        risk = WeatherRiskEnum.EXTREME
        reason = f"Extreme weather hazard: heavy rainfall ({rain_intensity:.1f} mm/h) or severe winds ({wind_speed:.1f} km/h). Maintenance operations strictly prohibited."
    elif rain_intensity >= 5.0 or wind_speed >= 40.0 or visibility_km <= 1.8 or rain_prob >= 70 or (is_welding and rain_prob >= 60):
        risk = WeatherRiskEnum.HIGH
        reason = f"High precipitation probability ({rain_prob}%) and rainfall intensity ({rain_intensity:.1f} mm/h) significantly impairs track welding and ballast tamping."
    elif rain_intensity >= 1.0 or wind_speed >= 22.0 or visibility_km <= 4.0 or rain_prob >= 35:
        risk = WeatherRiskEnum.MEDIUM
        reason = f"Moderate meteorological risk: light rain ({rain_intensity:.1f} mm/h) and reduced visibility ({visibility_km:.1f} km). Caution required."
    else:
        risk = WeatherRiskEnum.LOW
        reason = "Optimal meteorological conditions: clear sky, dry track bed, and high visibility."

    return risk, score, reason


def get_simulated_weather(
    section_id: str,
    time_min: Optional[int] = None,
    work_type: str = "Rail Replacement",
    override_risk: Optional[str] = None,
) -> SectionWeather:
    """
    Generates realistic, section-calibrated weather data from regional climate models when external APIs are unavailable.
    Labeled with weather_source='CALIBRATED_CLIMATE_MODEL'.
    """
    # Deterministic variation based on time of day (minutes past midnight)
    t = time_min if time_min is not None else 720  # default 12:00 PM

    # Resolve location coordinates & display name
    if section_id in SECTION_COORDINATES:
        coords = SECTION_COORDINATES[section_id]
        lat, lon, station_display = coords[0], coords[1], coords[2]
    else:
        try:
            from backend.services.station_network import find_station
            m = find_station(section_id)
            if m:
                lat, lon, station_display = float(m["lat"]), float(m["lon"]), f"{m['name']} · {m['code']}"
            else:
                lat, lon, station_display = DEFAULT_COORDINATES[0], DEFAULT_COORDINATES[1], DEFAULT_COORDINATES[2]
        except Exception:
            lat, lon, station_display = DEFAULT_COORDINATES[0], DEFAULT_COORDINATES[1], DEFAULT_COORDINATES[2]

    # Regional climate model: latitude-aware temperature (cooler in northern Jammu/Kashmir, temperate in Gangetic plains)
    lat_offset = (28.0 - lat) * 1.4
    base_temp = 28.0 + lat_offset
    temp = base_temp + 3.2 * math.sin((t - 480) / 720.0 * math.pi)
    rain_prob = int(max(5, 20 + 15 * math.sin((t - 600) / 360.0 * math.pi)))
    rain_intensity = max(0.0, (rain_prob - 25) * 0.08) if rain_prob > 25 else 0.0
    wind_speed = round(12.0 + 4.0 * math.cos(t / 360.0), 1)
    visibility = round(max(3.0, 9.5 - (rain_intensity * 1.2)), 1)
    condition = "Clear" if rain_prob < 30 else ("Scattered Clouds" if rain_prob < 50 else "Light Rain")

    # Apply manual override for testing specific operational conditions if requested
    if override_risk:
        override_upper = override_risk.upper()
        if override_upper == "EXTREME":
            rain_prob = 95
            rain_intensity = 22.5
            wind_speed = 65.0
            visibility = 0.4
            condition = "Severe Thunderstorm"
        elif override_upper == "HIGH":
            rain_prob = 75
            rain_intensity = 8.5
            wind_speed = 42.0
            visibility = 1.5
            condition = "Heavy Rain"
        elif override_upper == "MEDIUM":
            rain_prob = 45
            rain_intensity = 2.5
            wind_speed = 25.0
            visibility = 3.8
            condition = "Moderate Rain"
        elif override_upper == "LOW":
            rain_prob = 10
            rain_intensity = 0.0
            wind_speed = 11.0
            visibility = 9.5
            condition = "Clear"

    risk, score, reason = calculate_weather_risk_score(
        rain_prob=rain_prob,
        rain_intensity=rain_intensity,
        wind_speed=wind_speed,
        visibility_km=visibility,
        work_type=work_type,
    )

    # Regional air quality model
    if lat > 31.0:
        simulated_aqi = max(35, min(85, int(70 - (visibility * 3.0))))
    elif "DELHI" in station_display.upper() or "NDLS" in station_display.upper():
        simulated_aqi = max(80, min(240, int(155 - (visibility * 7.0))))
    else:
        simulated_aqi = max(45, min(140, int(110 - (visibility * 5.0))))

    if simulated_aqi <= 50:
        aqi_label = "Good"
    elif simulated_aqi <= 100:
        aqi_label = "Moderate"
    elif simulated_aqi <= 150:
        aqi_label = "Unhealthy for Sensitive"
    else:
        aqi_label = "Poor"

    return SectionWeather(
        section_id=section_id,
        temperature_c=round(temp, 1),
        rain_probability_pct=rain_prob,
        rainfall_intensity_mmh=round(rain_intensity, 1),
        wind_speed_kmph=wind_speed,
        visibility_km=visibility,
        weather_condition=condition,
        weather_risk=risk,
        weather_score=score,
        weather_reason=reason,
        weather_source="CALIBRATED_CLIMATE_MODEL",
        air_quality_index=simulated_aqi,
        air_quality_label=aqi_label,
        observed_at=datetime.now().isoformat(),
        forecast=[
            {"period": "next_2h", "condition": condition, "rain_probability_pct": min(100, rain_prob + 5), "wind_speed_kmph": wind_speed},
            {"period": "next_4h", "condition": "Cloudy" if rain_prob >= 30 else "Clear", "rain_probability_pct": rain_prob, "wind_speed_kmph": wind_speed},
        ],
        humidity_pct=round(65.0 - 5.0 * math.sin(t / 360.0), 1),
        weather_icon="☀️" if "Clear" in condition else ("🌧️" if "Rain" in condition else "⛅"),
        station_name=station_display,
    )


def get_section_weather(
    section_id: str,
    time_min: Optional[int] = None,
    work_type: str = "Rail Replacement",
    override_risk: Optional[str] = None,
) -> SectionWeather:
    """
    Fetches real-time weather data for a railway section.
    Utilizes in-memory TTL caching (5 minutes) and falls back gracefully to calibrated model if offline.
    """
    if override_risk:
        return get_simulated_weather(section_id, time_min, work_type, override_risk)

    cache_key = f"{section_id}_{time_min or 'cur'}_{work_type}"
    now_dt = datetime.now()
    if cache_key in _WEATHER_CACHE:
        entry = _WEATHER_CACHE[cache_key]
        if (now_dt - entry["cached_at"]).total_seconds() < WEATHER_CACHE_TTL_SECONDS:
            return entry["weather"]

    if section_id in SECTION_COORDINATES:
        coords = SECTION_COORDINATES[section_id]
    else:
        try:
            from backend.services.station_network import find_station
            st_match = find_station(section_id)
            if st_match:
                coords = (float(st_match["lat"]), float(st_match["lon"]), f"{st_match['name']} · {st_match['code']}")
            else:
                coords = DEFAULT_COORDINATES
        except Exception:
            coords = DEFAULT_COORDINATES
    lat, lon, station_name = coords

    # Attempt to query Open-Meteo free API
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m,visibility&hourly=precipitation_probability,temperature_2m,wind_speed_10m,visibility,weather_code&forecast_days=1&timezone=auto"
        res = requests.get(url, timeout=2.5)
        if res.status_code == 200:
            payload = res.json()
            data = payload.get("current", {})
            temp = float(data.get("temperature_2m", 28.0))
            humidity = float(data.get("relative_humidity_2m", 65.0))
            rain_intensity = float(data.get("precipitation", 0.0))
            wind_speed = float(data.get("wind_speed_10m", 12.0))
            vis_m = float(data.get("visibility", 8000.0))
            visibility_km = round(vis_m / 1000.0, 1)
            rain_prob = 80 if rain_intensity > 5.0 else (40 if rain_intensity > 0.5 else 15)

            weather_code = int(data.get("weather_code", 0))
            cond_tuple = WMO_WEATHER_MAP.get(weather_code)
            if cond_tuple:
                condition, icon = cond_tuple
            else:
                condition = "Clear sky" if weather_code <= 1 else ("Rain" if weather_code >= 51 else "Cloudy")
                icon = "☀️" if weather_code <= 1 else ("🌧️" if weather_code >= 51 else "☁️")

            # Try to fetch real air quality from Open-Meteo Air Quality API
            real_aqi = None
            try:
                aqi_res = requests.get(
                    f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&current=us_aqi",
                    timeout=1.8,
                )
                if aqi_res.status_code == 200:
                    val = aqi_res.json().get("current", {}).get("us_aqi")
                    if val is not None:
                        real_aqi = int(val)
            except Exception:
                pass

            if real_aqi is None:
                real_aqi = max(40, min(290, int(150 - (visibility_km * 8))))

            if real_aqi <= 50:
                aqi_desc = "Good"
            elif real_aqi <= 100:
                aqi_desc = "Moderate"
            elif real_aqi <= 150:
                aqi_desc = "Unhealthy (Sensitive)"
            else:
                aqi_desc = "Poor"

            risk, score, reason = calculate_weather_risk_score(
                rain_prob=rain_prob,
                rain_intensity=rain_intensity,
                wind_speed=wind_speed,
                visibility_km=visibility_km,
                work_type=work_type,
            )
            hourly = payload.get("hourly", {})
            forecast = []
            for index, timestamp in enumerate(hourly.get("time", [])[:4]):
                h_code = int(hourly.get("weather_code", [])[index]) if index < len(hourly.get("weather_code", [])) else 0
                h_cond, h_icon = WMO_WEATHER_MAP.get(h_code, ("Clear", "☀️"))
                forecast.append({
                    "period": timestamp,
                    "temperature_c": hourly.get("temperature_2m", [])[index],
                    "rain_probability_pct": hourly.get("precipitation_probability", [])[index],
                    "wind_speed_kmph": hourly.get("wind_speed_10m", [])[index],
                    "visibility_km": round(hourly.get("visibility", [])[index] / 1000.0, 1),
                    "condition": h_cond,
                    "icon": h_icon,
                })

            # Persist weather snapshot to Supabase
            try:
                from backend.services import supabase_train_store as supa_store
                stn_code = "CNB" if "CNB" in section_id or "KNP" in section_id else "PRYJ"
                supa_store.store_weather_snapshot(
                    stn_code,
                    {
                        "temperature_c": temp,
                        "humidity_pct": humidity,
                        "rain_mm": rain_intensity,
                        "rain_probability_pct": rain_prob,
                        "wind_speed_kmph": wind_speed,
                        "weather_condition": condition,
                        "data_source": "OPEN_METEO_API",
                    },
                )
            except Exception:
                pass

            res_weather = SectionWeather(
                section_id=section_id,
                temperature_c=temp,
                rain_probability_pct=rain_prob,
                rainfall_intensity_mmh=rain_intensity,
                wind_speed_kmph=wind_speed,
                visibility_km=visibility_km,
                weather_condition=condition,
                weather_risk=risk,
                weather_score=score,
                weather_reason=reason,
                weather_source="OPEN_METEO_API",
                air_quality_index=real_aqi,
                air_quality_label=aqi_desc,
                observed_at=datetime.now().isoformat(),
                forecast=forecast,
                humidity_pct=humidity,
                weather_icon=icon,
                station_name=station_name,
            )
            _WEATHER_CACHE[cache_key] = {"cached_at": datetime.now(), "weather": res_weather}
            return res_weather
    except Exception:
        # Fallback cleanly without crashing
        pass

    fallback_weather = get_simulated_weather(section_id, time_min, work_type, override_risk)
    _WEATHER_CACHE[cache_key] = {"cached_at": datetime.now(), "weather": fallback_weather}
    return fallback_weather
