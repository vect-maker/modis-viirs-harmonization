from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from model.FireCluster import FireCluster


class FireClusterForecast(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)

    fireClusterId: int = Field(foreign_key="firecluster.id", nullable=False, index=True)

    dirExpansion: float | None = Field(default=None, nullable=True)
    cardinalDirection: str | None = Field(default=None, nullable=True)
    veloExpansion: float | None = Field(default=None, nullable=True)
    distanceKm: float | None = Field(default=None, nullable=True)
    calculatedAt: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)

    fireCluster: "FireCluster" = Relationship(
        back_populates="forecasts",
        sa_relationship_kwargs={
            "foreign_keys": "[FireClusterForecast.fireClusterId]"
        },
    )
