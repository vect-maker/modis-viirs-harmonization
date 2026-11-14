from sqlmodel import Field, SQLModel, Relationship

from model.FireCluster import FireCluster
from model.Hotspot import Hotspot


from sqlmodel import SQLModel, Field, Relationship

class ClusterHotspot(SQLModel, table=True):

    clusterId: int = Field(
        foreign_key="firecluster.id",
        primary_key=True
    )

    hotspotId: int = Field(
        foreign_key="hotspot.id",
        primary_key=True
    )

    cluster: "FireCluster" = Relationship(
        back_populates="hotspots"
    )

    hotspot: "Hotspot" = Relationship(
        back_populates="clusters"
    )