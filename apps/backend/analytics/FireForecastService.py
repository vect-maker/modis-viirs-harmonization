import math
from datetime import datetime

CARDINAL_DIRECTIONS = (
    "Norte",
    "Noreste",
    "Este",
    "Sureste",
    "Sur",
    "Suroeste",
    "Oeste",
    "Noroeste",
)


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula el rumbo (bearing) en grados [0, 360) desde (lat1, lon1) hasta (lat2, lon2).
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lon = math.radians(lon2 - lon1)

    y = math.sin(delta_lon) * math.cos(phi2)
    x = (
        math.cos(phi1) * math.sin(phi2)
        - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lon)
    )

    theta = math.atan2(y, x)
    return (math.degrees(theta) + 360.0) % 360.0


def bearing_to_cardinal(degrees: float) -> str:
    """
    Convierte un ángulo en grados [0, 360) a la dirección cardinal más cercana.
    """
    index = round(degrees / 45.0) % 8
    return CARDINAL_DIRECTIONS[index]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Distancia geodésica Haversine entre dos puntos en kilómetros.
    """
    earth_radius_km = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    )
    return earth_radius_km * 2.0 * math.asin(math.sqrt(a))


def compute_cluster_expansion(
    points: list[tuple[float, float, datetime]],
) -> dict[str, float | str]:
    """
    Calcula dirección y velocidad de expansión a partir de una lista de
    puntos (latitude, longitude, acq_datetime).
    """
    if len(points) < 2:
        return {
            "dirExpansion": 0.0,
            "cardinalDirection": "Norte",
            "distanceKm": 0.0,
            "veloExpansion": 0.0,
        }

    ordered = sorted(points, key=lambda p: p[2])
    first_lat, first_lon, first_dt = ordered[0]
    last_lat, last_lon, last_dt = ordered[-1]

    # Rumbo neto desde el primer hotspot al último
    bearing = calculate_bearing(first_lat, first_lon, last_lat, last_lon)
    cardinal = bearing_to_cardinal(bearing)

    # Distancia total recorrida sumando tramos consecutivos
    total_distance_km = sum(
        haversine_km(ordered[i][0], ordered[i][1], ordered[i + 1][0], ordered[i + 1][1])
        for i in range(len(ordered) - 1)
    )

    elapsed_hours = (last_dt - first_dt).total_seconds() / 3600.0
    velocity_kmh = total_distance_km / elapsed_hours if elapsed_hours > 0 else 0.0

    return {
        "dirExpansion": round(bearing, 4),
        "cardinalDirection": cardinal,
        "distanceKm": round(total_distance_km, 4),
        "veloExpansion": round(velocity_kmh, 4),
    }
