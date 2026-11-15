from collections.abc import Sequence

from sqlmodel import Session, SQLModel, func, select
from sqlmodel.sql.expression import SelectOfScalar

from schemas.pagination import PaginatedResponse, PaginationParams


def paginate_statement[ModelT: SQLModel, PublicT: SQLModel](
    session: Session,
    statement: SelectOfScalar[ModelT],
    pagination: PaginationParams,
    public_model: type[PublicT],
) -> PaginatedResponse[PublicT]:
    """Execute a paginated select statement and map rows to the public schema."""
    count_stmt = select(func.count()).select_from(statement.subquery())
    total = session.exec(count_stmt).one()
    rows = session.exec(
        statement.offset(pagination.offset).limit(pagination.limit)
    ).all()
    return PaginatedResponse(
        data=[public_model.model_validate(row) for row in rows],
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )


def paginate_sequence[T](
    items: Sequence[T],
    pagination: PaginationParams,
) -> PaginatedResponse[T]:
    """Slice an in-memory sequence into a standard PaginatedResponse."""
    total = len(items)
    sliced = list(items[pagination.offset : pagination.offset + pagination.limit])
    return PaginatedResponse(
        data=sliced,
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )
