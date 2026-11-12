from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# 401/403 come from libs/auth (JWTAuth) as HTTPExceptions, so they aren't defined here.


class OrderServiceError(Exception):
    status_code = 400
    detail = "Bad request"


class OrderNotFound(OrderServiceError):
    # Also returned for other users' orders, so ids of existing orders aren't revealed
    status_code = 404
    detail = "Order not found"


class OrderNotCancellable(OrderServiceError):
    status_code = 409
    detail = "Only pending orders can be cancelled"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(OrderServiceError)
    async def _handle(request: Request, exc: OrderServiceError) -> JSONResponse:
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
