from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class UserServiceError(Exception):
    status_code = 400
    detail = "Bad request"


class EmailTaken(UserServiceError):
    status_code = 409
    detail = "Email is already registered"


class InvalidCredentials(UserServiceError):
    status_code = 401
    detail = "Invalid email or password"


class InvalidToken(UserServiceError):
    status_code = 401
    detail = "Invalid or expired token"


class Forbidden(UserServiceError):
    status_code = 403
    detail = "Not enough permissions"


class UserNotFound(UserServiceError):
    status_code = 404
    detail = "User not found"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(UserServiceError)
    async def _handle(request: Request, exc: UserServiceError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=headers)
