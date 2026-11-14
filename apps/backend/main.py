from contextlib import asynccontextmanager

from fastapi import FastAPI

from controller.hostpostController import router as hostpot_router
from database.initDb import create_db_and_tables
from enviromental.WeatherDataClient import router as weather_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(weather_router)
app.include_router(hostpot_router)


@app.get("/")
async def root():
    return {"message": "Servidor funcionando"}
