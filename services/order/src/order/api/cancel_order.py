from uuid import UUID

from fastapi import APIRouter

from order.dependencies import CurrentClaims
from order.schemas.order import CancelOrderInput, OrderOutput
from order.services.cancel_order import cancel_order as cancel_order_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/{order_id}/cancel", response_model=OrderOutput)
async def cancel_order(
    order_id: UUID,
    claims: CurrentClaims,
    body: CancelOrderInput | None = None,
):
    reason = body.reason if body else None
    return await cancel_order_service(order_id, claims.user_id, reason)
