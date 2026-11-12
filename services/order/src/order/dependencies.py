from pathlib import Path
from typing import Annotated

from aiokafka import AIOKafkaProducer
from auth import AccessClaims, JWTAuth
from fastapi import Depends, Request

from order.config import settings

# Read at import, so a missing key stops the service at startup, not on the first request.
auth = JWTAuth(Path(settings.jwt_public_key_path).read_text())
CurrentClaims = Annotated[AccessClaims, Depends(auth)]


def get_producer(request: Request) -> AIOKafkaProducer:
    """The producer started in main.lifespan."""
    return request.app.state.producer


Producer = Annotated[AIOKafkaProducer, Depends(get_producer)]
