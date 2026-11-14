from sqlmodel import Session, select

from model.Hotspots import Hotspots


class HotspotRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_hotspots(self):
        statement = select(Hotspots).offset(0).limit(50)
        return self.session.exec(statement).all()

    def get_hostspot_by_dates(self, start_date: str, end_date: str):
        statement = (
            select(Hotspots)
            .where(Hotspots.acq_datetime >= start_date)
            .where(Hotspots.acq_datetime <= end_date)
            .offset(0)
        )
        return self.session.exec(statement).all()

    def get_hostspot_by_location(self, latitude: float, longitude: float):
        statement = (
            select(Hotspots)
            .where(Hotspots.latitude == latitude)
            .where(Hotspots.longitude == longitude)
            .offset(0)
        )
        return self.session.exec(statement).all()
