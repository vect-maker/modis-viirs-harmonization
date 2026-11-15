from sqlmodel import Session, col, select

from model.StarSchema import CountryPublic, DimCountry
from repositories.pagination import paginate_statement
from schemas.pagination import PaginatedResponse, PaginationParams


class CountryRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_countries(
        self, pagination: PaginationParams
    ) -> PaginatedResponse[CountryPublic]:
        statement = select(DimCountry).order_by(
            col(DimCountry.name),
            col(DimCountry.id),
        )
        return paginate_statement(self.session, statement, pagination, CountryPublic)
