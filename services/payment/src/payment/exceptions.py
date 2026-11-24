from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class PaymentServiceError(Exception):
    status_code = 400
    detail = "Bad request"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(PaymentServiceError)
    async def _handle(request: Request, exc: PaymentServiceError) -> JSONResponse:
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
