from datetime import datetime

from sqlmodel import Field, SQLModel, Relationship

from model.ClusterHotspot import ClusterHotspot

class Hotspot(SQLModel, table = True):

    id: int = Field(default=None,primary_key=True)

    latitude: float = Field(default=None)

    longitude: float = Field(default=None)

    bright_mir: float = Field(default=None)

    scan: float = Field(default=None)

    track: float = Field(default=None)

    acq_datetime: datetime = Field(default=None, index=True)

    satellite: str = Field(default=None)

    instrument: str = Field(default=None)

    confidence: int = Field(ge=0, le=100, default=None)

    confidence_class: str = Field(default=None)

    version: str = Field(default=None)

    bright_tir: float = Field(default=None)

    frp: float = Field(default=None)

    daynight: bool= Field(default=None)

    type: bool = Field(default=None)

    clusters: list["ClusterHotspot"] = Relationship(
        back_populates="hotspot"
    )