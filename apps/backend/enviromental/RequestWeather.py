from datetime import datetime

from sqlmodel import Field, SQLModel


class RequestWeather(SQLModel):
    latitude: float = Field(nullable=False)
    longitude: float = Field(nullable=False)
    start: datetime = Field(nullable=False)
    end: datetime = Field(nullable=False)
    parameters: str = "T2M,ALLSKY_SFC_SW_DWN,RH2M"
    community: str = "AG"
