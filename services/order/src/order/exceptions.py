from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class OrderServiceError(Exception):
    status_code = 400
    detail = "Bad request"


class OrderNotFound(OrderServiceError):
    status_code = 404
    detail = "Order not found"


class IdempotencyKeyReused(OrderServiceError):
    status_code = 422
    detail = "Idempotency-Key was already used with a different request"


class OrderNotCancellable(OrderServiceError):
    status_code = 409
    detail = "Only pending orders can be cancelled"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(OrderServiceError)
    async def _handle(request: Request, exc: OrderServiceError) -> JSONResponse:
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
