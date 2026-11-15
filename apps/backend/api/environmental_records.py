from fastapi import APIRouter, Depends
from sqlmodel import Session, col, select

from database.session import get_session
from model import EnvironmentalRecord
from repositories.pagination import paginate_statement
from schemas.pagination import PaginatedResponse, PaginationDep

router = APIRouter(prefix="/environmental-records", tags=["EnvironmentalRecords"])


@router.get("", summary="Listar registros ambientales")
async def get_environmental_records(
    pagination: PaginationDep,
    session: Session = Depends(get_session),
) -> PaginatedResponse[EnvironmentalRecord]:
    stmt = select(EnvironmentalRecord).order_by(col(EnvironmentalRecord.id))
    return paginate_statement(session, stmt, pagination, EnvironmentalRecord)
