from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from model.FireCluster import FireCluster


class ClusterHotspots(SQLModel, table=True):
    clusterId: int = Field(foreign_key="firecluster.id", primary_key=True)
    hotspotsId: int = Field(primary_key=True)

    cluster: "FireCluster" = Relationship(back_populates="hotspots")