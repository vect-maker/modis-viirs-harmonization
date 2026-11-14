from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    try:
        from .FireCluster import FireCluster
        from .Hotspots import Hotspots
    except ImportError:
        from model.FireCluster import FireCluster
        from model.Hotspots import Hotspots


class ClusterHotspots(SQLModel, table=True):
    clusterId: int = Field(foreign_key="firecluster.id", primary_key=True)
    hotspotsId: int = Field(foreign_key="hotspots.id", primary_key=True)

    cluster: "FireCluster" = Relationship(back_populates="hotspots")
    hotspots: "Hotspots" = Relationship(back_populates="clusters")
