from sqlmodel import Session, select

from model import Hotspots


class HotspotRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_hotspots(self, limit: int = 50, offset: int = 0) -> list[Hotspots]:
        statement = select(Hotspots).offset(offset).limit(limit)
        return self.session.exec(statement).all()
