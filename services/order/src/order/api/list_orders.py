from typing import Annotated

from fastapi import APIRouter, Query

from order.dependencies import CurrentClaims
from order.schemas.order import OrderListOutput
from order.services.list_orders import list_orders as list_orders_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", response_model=OrderListOutput)
async def list_orders(
    claims: CurrentClaims,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return await list_orders_service(claims.user_id, limit, offset)
