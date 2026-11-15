from typing import Annotated

from fastapi import Query
from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """Query parameters for offset-based pagination."""

    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of items to return",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of items to skip",
    )


PaginationDep = Annotated[PaginationParams, Query()]


class PaginatedResponse[T](BaseModel):
    """Standard paginated response envelope matching { data, total, limit, offset }."""

    data: list[T]
    total: int
    limit: int
    offset: int
