from __future__ import annotations
from typing import Generic, TypeVar, Optional, Any

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")
CreateT = TypeVar("CreateT")
UpdateT = TypeVar("UpdateT")
ResponseT = TypeVar("ResponseT")


class BaseService(Generic[ModelT, CreateT, UpdateT, ResponseT]):
    def __init__(self, model: type[ModelT], response_schema: type[ResponseT]):
        self.model = model
        self.response_schema = response_schema

    async def get_or_404(self, db: AsyncSession, *filters, options=None) -> ModelT:
        query = select(self.model).where(*filters)
        if options:
            query = query.options(*options)
        result = await db.execute(query)
        entity = result.scalar_one_or_none()
        if not entity:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"{self.model.__name__} not found")
        return entity

    async def get_or_none(self, db: AsyncSession, *filters, options=None) -> Optional[ModelT]:
        query = select(self.model).where(*filters)
        if options:
            query = query.options(*options)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def list_all(self, db: AsyncSession, *filters, order_by=None, limit=None, options=None) -> list[ModelT]:
        query = select(self.model).where(*filters)
        if options:
            query = query.options(*options)
        if order_by is not None:
            query = query.order_by(order_by)
        if limit is not None:
            query = query.limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, data: CreateT, **extra_fields) -> ResponseT:
        entity = self.model(**data.model_dump(), **extra_fields)
        db.add(entity)
        await db.flush()
        result = self.response_schema.model_validate(entity)
        await db.commit()
        return result

    async def update(self, db: AsyncSession, entity: ModelT, data: UpdateT) -> ResponseT:
        for key, val in data.model_dump(exclude_unset=True).items():
            setattr(entity, key, val)
        await db.flush()
        result = self.response_schema.model_validate(entity)
        await db.commit()
        return result

    async def delete(self, db: AsyncSession, entity: ModelT) -> None:
        await db.delete(entity)
        await db.commit()

    async def paginate(
        self,
        db: AsyncSession,
        base_query,
        count_query,
        page: int = 1,
        limit: int = 50,
        order_by=None,
    ) -> tuple[list[ModelT], int]:
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        offset = (page - 1) * limit
        query = base_query.order_by(order_by).offset(offset).limit(limit) if order_by is not None \
            else base_query.offset(offset).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all()), total
