from sqlmodel import Session, col, select

from model.StarSchema import FactHotspot, HotspotPublic
from repositories.pagination import paginate_statement
from schemas.pagination import PaginatedResponse, PaginationParams


class HotspotRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_hotspots(
        self, pagination: PaginationParams
    ) -> PaginatedResponse[HotspotPublic]:
        statement = select(FactHotspot).order_by(
            col(FactHotspot.acq_datetime).desc(),
            col(FactHotspot.id),
        )
        return paginate_statement(self.session, statement, pagination, HotspotPublic)
