from __future__ import annotations

from fastapi import APIRouter

from api.charts.diagnostics import router as diagnostics_router
from api.charts.models import router as models_router
from api.charts.temporal import router as temporal_router

router = APIRouter(prefix="/charts")
router.include_router(temporal_router)
router.include_router(diagnostics_router)
router.include_router(models_router)

__all__ = [
    "router",
    "temporal_router",
    "diagnostics_router",
    "models_router",
]
