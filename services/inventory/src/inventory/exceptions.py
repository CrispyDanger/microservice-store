from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class InventoryServiceError(Exception):
    status_code = 400
    detail = "Bad request"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(InventoryServiceError)
    async def _handle(request: Request, exc: InventoryServiceError) -> JSONResponse:
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
