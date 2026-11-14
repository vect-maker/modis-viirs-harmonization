from sqlmodel import Session, col, select

from model.StarSchema import DimPlatform, PlatformPublic
from repositories.pagination import paginate_statement
from schemas.pagination import PaginatedResponse, PaginationParams


class PlatformRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_platforms(
        self, pagination: PaginationParams
    ) -> PaginatedResponse[PlatformPublic]:
        statement = select(DimPlatform).order_by(
            col(DimPlatform.satellite),
            col(DimPlatform.instrument),
            col(DimPlatform.id),
        )
        return paginate_statement(self.session, statement, pagination, PlatformPublic)
