"""FX rate read API. Currently exposes USD/CNY via Bank of China."""

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.models.user import User
from app.services.fx import get_usd_cny

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/fx", tags=["fx"])


class UsdCnyResponse(BaseModel):
    pair: str
    rate: float
    fetched_at: float
    published_at: Optional[str] = None
    source: str


@router.get("/usd-cny", response_model=UsdCnyResponse)
async def usd_cny(
    current_user: Annotated[User, Depends(get_current_user)],
    refresh: bool = Query(False, description="Force re-fetch, bypassing the 10-min cache"),
):
    """Latest USD/CNY rate from Bank of China (10-min cache)."""
    try:
        fx = await get_usd_cny(force_refresh=refresh)
    except Exception as exc:
        logger.warning("BoC fetch failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not fetch USD/CNY from Bank of China: {exc}",
        )
    return UsdCnyResponse(**fx.to_dict())
