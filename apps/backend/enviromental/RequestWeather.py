from datetime import datetime

from sqlmodel import SQLModel, Field


class RequestWeather(SQLModel, table = False):

    latitude: float= Field(default=None,nullable=False)

    longitude: float= Field(default=None,nullable=False)

    start: datetime = Field(default=None,nullable=False)

    end: datetime = Field(default=None,nullable=False)

    parameters: str = "T2M,ALLSKY_SFC_SW_DWN,RH2M"

    community: str = "AG"