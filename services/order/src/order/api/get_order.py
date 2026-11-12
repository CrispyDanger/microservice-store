from uuid import UUID

from fastapi import APIRouter

from order.dependencies import CurrentClaims
from order.schemas.order import OrderOutput
from order.services.get_order import get_order as get_order_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/{order_id}", response_model=OrderOutput)
async def get_order(order_id: UUID, claims: CurrentClaims):
    return await get_order_service(order_id, claims.user_id)
