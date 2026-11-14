from contextlib import asynccontextmanager

from fastapi import FastAPI

try:
    from apps.backend.controller.hostpostController import router as hostpot_router
    from apps.backend.database.initDb import create_db_and_tables
except ImportError:
    from controller.hostpostController import router as hostpot_router
    from database.initDb import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield


app = FastAPI(
    title="Fire Detection API",
    description="API para monitoreo y consulta de hotspots de incendios",
    lifespan=lifespan,
)

app.include_router(hostpot_router)


@app.get("/")
async def root():
    return {"message": "Servidor funcionando"}
