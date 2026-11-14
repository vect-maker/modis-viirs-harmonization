from sqlmodel import Session, select

from model import Hotspots

class HotspotRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_hotspots(self):
        statement = select(Hotspots).offset(0).limit(50)

        return self.session.exec(statement).all()



    