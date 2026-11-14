from typing import Literal

from pydantic import BaseModel

HealthStatus = Literal["ok", "error"]


class HealthLiveResponse(BaseModel):
    """Liveness probe response confirming the FastAPI process is running."""

    status: Literal["ok"]


class HealthReadyResponse(BaseModel):
    """Readiness probe response reporting overall status and per-dependency health."""

    status: HealthStatus
    dependencies: dict[str, HealthStatus]
