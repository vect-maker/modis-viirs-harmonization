"""Cliente reutilizable para consultar datos meteorológicos diarios de NASA POWER."""

from __future__ import annotations

from typing import Any

import httpx

from enviromental.RequestWeather import RequestWeather

NASA_POWER_DAILY_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
NASA_MISSING_SENTINEL = -999.0


class WeatherClientError(RuntimeError):
    """Error al consultar o interpretar datos de la API de NASA POWER."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


class WeatherDataClient:
    """Consulta y normaliza registros diarios desde NASA POWER sin inventar faltantes."""

    def __init__(
        self,
        base_url: str = NASA_POWER_DAILY_URL,
        timeout: float = 20.0,
    ) -> None:
        self.base_url = base_url
        self.timeout = timeout

    @staticmethod
    def _sanitize_value(value: Any) -> float | None:
        if value is None:
            return None
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        if numeric <= NASA_MISSING_SENTINEL:
            return None
        return numeric

    @classmethod
    def parse_daily_records(cls, raw: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Convierte la respuesta JSON de NASA POWER en una lista ordenada por fecha.
        Los valores sentinela (-999) se convierten a None.
        """
        properties = raw.get("properties", {})
        parameter_data = properties.get("parameter", {})
        if not parameter_data:
            return []

        first_param = next(iter(parameter_data.values()))
        dates = sorted(first_param.keys())

        records: list[dict[str, Any]] = []
        for date_str in dates:
            record: dict[str, Any] = {"date": date_str}
            for param_name, param_values in parameter_data.items():
                record[param_name] = cls._sanitize_value(param_values.get(date_str))
            records.append(record)

        return records

    async def fetch_raw(self, data: RequestWeather) -> dict[str, Any]:
        """Realiza la petición HTTP GET a NASA POWER."""
        params = {
            "latitude": data.latitude,
            "longitude": data.longitude,
            "start": data.start.strftime("%Y%m%d"),
            "end": data.end.strftime("%Y%m%d"),
            "parameters": data.parameters,
            "community": data.community,
            "format": "JSON",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(self.base_url, params=params)
            except httpx.HTTPError as exc:
                raise WeatherClientError(
                    f"Error de conexión con NASA POWER: {exc}",
                    status_code=502,
                ) from exc

        if response.status_code != 200:
            raise WeatherClientError(
                "Error al consultar la API de NASA POWER",
                status_code=response.status_code,
            )

        return response.json()

    async def fetch_daily_records(self, data: RequestWeather) -> list[dict[str, Any]]:
        """Obtiene y normaliza los registros diarios desde NASA POWER."""
        raw = await self.fetch_raw(data)
        return self.parse_daily_records(raw)
