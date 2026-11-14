from fastapi import FastAPI
import httpx

from enviromental.RequestWeather import RequestWeather

app = FastAPI()

@app.post("/weather/")
async def getweatherparams(data: RequestWeather, tags=["Weather"]):
    params = {
        "latitude": data.latitude,
        "longitude": data.longitude,
        "start": data.start.strftime("%Y%m%d"),
        "end": data.end.strftime("%Y%m%d"),
        "parameters": ",".join(data.parameters),
        "community": data.community,
        "format": "JSON"
    }

    url = "https://power.larc.nasa.gov/api/temporal/daily/point"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)

    return response.json()

