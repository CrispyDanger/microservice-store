from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header

from order.dependencies import CurrentClaims
from order.schemas.order import OrderOutput, PlaceOrderInput
from order.services.place_order import place_order as place_order_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderOutput, status_code=201)
async def place_order(
    body: PlaceOrderInput,
    claims: CurrentClaims,
    idempotency_key: Annotated[UUID, Header()],
):
    return await place_order_service(body, claims.user_id, idempotency_key)
