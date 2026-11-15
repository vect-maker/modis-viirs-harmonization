from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    try:
        from .FireCluster import FireCluster
    except ImportError:
        from model.FireCluster import FireCluster


class EnvironmentalRecord(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    datetimeStart: datetime | None = Field(default=None, nullable=True)
    humidity: float | None = Field(default=None, nullable=True)
    precipitation: float | None = Field(default=None, nullable=True)
    temperature: float | None = Field(default=None, nullable=True)
    windSpeed: float | None = Field(default=None, nullable=True)
    windDirection: float | None = Field(default=None, nullable=True)
    vegetationType: float | None = Field(default=None, nullable=True)
    densityVegetation: float | None = Field(default=None, nullable=True)
    nubosity: float | None = Field(default=None, nullable=True)

    fireClusterId: int | None = Field(
        default=None,
        foreign_key="firecluster.id",
    )

    fireCluster: "FireCluster" = Relationship(
        back_populates="environmentalRecords",
        sa_relationship_kwargs={"foreign_keys": "[EnvironmentalRecord.fireClusterId]"},
    )
