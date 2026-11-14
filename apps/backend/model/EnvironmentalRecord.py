from datetime import datetime

from sqlmodel import Field, SQLModel


class EnvironmentalRecord(SQLModel, table=True):

    id: int = Field(default=None,primary_key=True)

    datetimeStart: datetime= Field(default=None,nullable=True)

    humidity: float= Field(default=None,nullable=True)

    precipitation: float= Field(default=None,nullable=True)

    temperature: float= Field(default=None,nullable=True)

    windSpeed: float= Field(default=None,nullable=True)

    windDirection: float= Field(default=None,nullable=True)

    vegetationType: float= Field(default=None,nullable=True)

    densityVegetation: float= Field(default=None,nullable=True)

    nubosity: float= Field(default=None,nullable=True)

