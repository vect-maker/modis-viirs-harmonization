from sqlmodel import Session, SQLModel, select

from model import Hotspots


class HotspotRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_hotspots(self):
        statement = select(Hotspots)

        return self.session.exec(statement).all()