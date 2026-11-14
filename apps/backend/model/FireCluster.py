from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING


from model.ClusterStatus import ClusterStatus
from model.EnvironmentalRecord import EnvironmentalRecord

from sqlmodel import Field, SQLModel, create_engine, Relationship

if TYPE_CHECKING:
    from model.ClusterHotspot import ClusterHotspot

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


    environmentalRecords: list["EnvironmentalRecord"] = Relationship(
        back_populates="fireCluster",
        sa_relationship_kwargs={
            "foreign_keys": "[EnvironmentalRecord.fireClusterId]"
        }
    )

    dirExpansion: float= Field(default=None,nullable=True)

    veloExpansion: float= Field(default=None,nullable=True)
