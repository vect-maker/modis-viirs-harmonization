from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, SQLModel, Relationship

from model import FireCluster

if TYPE_CHECKING:
    from model.FireCluster import FireCluster

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

    fireClusterId: int | None = Field(
        default=None,
        foreign_key="firecluster.id"
    )

    fireCluster: "FireCluster" = Relationship(
        back_populates="environmentalRecords",
        sa_relationship_kwargs={
            "foreign_keys": "[EnvironmentalRecord.fireClusterId]"
        }
    )