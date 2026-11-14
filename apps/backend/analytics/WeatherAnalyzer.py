"""Integración y análisis vectorial de condiciones meteorológicas."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from analytics.FireMovementAnalyzer import _angular_difference_deg

REQUIRED_WEATHER_FIELDS = (
    "wind_speed",
    "wind_direction_from_deg",
    "temperature",
    "humidity",
    "precipitation",
)


@dataclass(slots=True)
class WeatherAnalysisResult:
    """Resultado del análisis meteorológico sin datos inventados."""

    is_complete: bool
    missing_variables: list[str]
    wind_speed: float | None
    wind_direction_from_deg: float | None
    wind_direction_to_deg: float | None
    wind_u: float | None
    wind_v: float | None
    temperature: float | None
    humidity: float | None
    precipitation: float | None
    wind_fire_angle_diff_deg: float | None = None
    wind_fire_alignment_cos: float | None = None
    status_message: str = "Análisis meteorológico completo"


class WeatherAnalyzer:
    """
    Normaliza variables meteorológicas de NASA POWER o EnvironmentalRecord,
    convierte la dirección meteorológica del viento ("desde donde viene") a
    vector de desplazamiento ("hacia donde va") y evalúa su relación con el fuego.
    """

    @staticmethod
    def _extract_numeric(record: Any, *keys: str) -> float | None:
        for key in keys:
            val = record.get(key) if isinstance(record, Mapping) else getattr(record, key, None)
            if val is not None:
                try:
                    num = float(val)
                    if not math.isnan(num) and num > -999.0:
                        return num
                except (TypeError, ValueError):
                    continue
        return None

    @staticmethod
    def wind_to_vector(
        wind_speed: float,
        wind_from_deg: float,
    ) -> tuple[float, float, float]:
        """
        Convierte dirección meteorológica (desde donde viene el viento) en
        dirección de desplazamiento (hacia donde va) y componentes vectoriales:
          u = V * sin(theta)  [componente Este-Oeste]
          v = V * cos(theta)  [componente Norte-Sur]
        """
        if wind_speed < 0:
            raise ValueError("wind_speed no puede ser negativo")

        wind_to_deg = (wind_from_deg + 180.0) % 360.0
        theta_rad = math.radians(wind_to_deg)
        u = wind_speed * math.sin(theta_rad)
        v = wind_speed * math.cos(theta_rad)
        return wind_to_deg, u, v

    def analyze(
        self,
        weather_record: Any | None,
        fire_direction_deg: float | None = None,
    ) -> WeatherAnalysisResult:
        """
        Analiza un registro meteorológico y opcionalmente lo compara contra la
        dirección observada de propagación del incendio.
        Si faltan variables o no hay registro, marca is_complete=False sin inventar datos.
        """
        if weather_record is None:
            return WeatherAnalysisResult(
                is_complete=False,
                missing_variables=list(REQUIRED_WEATHER_FIELDS),
                wind_speed=None,
                wind_direction_from_deg=None,
                wind_direction_to_deg=None,
                wind_u=None,
                wind_v=None,
                temperature=None,
                humidity=None,
                precipitation=None,
                status_message="Análisis meteorológico incompleto: no existen datos disponibles.",
            )

        wind_speed = self._extract_numeric(weather_record, "WS10M", "windSpeed", "wind_speed")
        wind_from = self._extract_numeric(weather_record, "WD10M", "windDirection", "wind_direction_from_deg")
        temperature = self._extract_numeric(weather_record, "T2M", "temperature")
        humidity = self._extract_numeric(weather_record, "RH2M", "humidity")
        precipitation = self._extract_numeric(weather_record, "PRECTOTCORR", "precipitation")

        values_map = {
            "wind_speed": wind_speed,
            "wind_direction_from_deg": wind_from,
            "temperature": temperature,
            "humidity": humidity,
            "precipitation": precipitation,
        }
        missing = [name for name, val in values_map.items() if val is None]

        wind_to_deg: float | None = None
        wind_u: float | None = None
        wind_v: float | None = None
        angle_diff: float | None = None
        alignment_cos: float | None = None

        if wind_speed is not None and wind_from is not None and wind_speed >= 0:
            wind_to_deg, wind_u, wind_v = self.wind_to_vector(wind_speed, wind_from)
            wind_to_deg = round(wind_to_deg, 4)
            wind_u = round(wind_u, 4)
            wind_v = round(wind_v, 4)

            if fire_direction_deg is not None:
                angle_diff = round(_angular_difference_deg(wind_to_deg, fire_direction_deg), 4)
                alignment_cos = round(math.cos(math.radians(angle_diff)), 4)

        is_complete = len(missing) == 0
        status_msg = (
            "Análisis meteorológico completo"
            if is_complete
            else f"Análisis meteorológico incompleto: faltan {', '.join(missing)}"
        )

        return WeatherAnalysisResult(
            is_complete=is_complete,
            missing_variables=missing,
            wind_speed=wind_speed,
            wind_direction_from_deg=wind_from,
            wind_direction_to_deg=wind_to_deg,
            wind_u=wind_u,
            wind_v=wind_v,
            temperature=temperature,
            humidity=humidity,
            precipitation=precipitation,
            wind_fire_angle_diff_deg=angle_diff,
            wind_fire_alignment_cos=alignment_cos,
            status_message=status_msg,
        )
