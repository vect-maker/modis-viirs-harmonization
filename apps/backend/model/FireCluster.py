from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel, create_engine, Relationship

from model.ClusterHotspot import ClusterHotspot
from model.ClusterStatus import ClusterStatus
from model.EnvironmentalRecord import EnvironmentalRecord

class FireCluster(SQLModel, table = True):

    id: int = Field(default=None,primary_key=True)

    hotspots: list["ClusterHotspot"] = Relationship(
        back_populates="cluster"
    )

    polygon: float= Field(default=None, nullable=False)

    status: str= Field(default=ClusterStatus.ACTIVO,nullable=False)

    datetimeStart: datetime= Field(default=None,nullable=True)

    datetimeEnd: datetime= Field(default=None,nullable=True)

    maxFrp: float= Field(default=None,nullable=True)

    environmentalRecord: EnvironmentalRecord = Field(default=None,nullable=True)

    dirExpansion: float= Field(default=None,nullable=True)

    veloExpansion: float= Field(default=None,nullable=True)
