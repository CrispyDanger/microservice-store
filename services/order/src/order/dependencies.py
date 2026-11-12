from pathlib import Path
from typing import Annotated

from aiokafka import AIOKafkaProducer
from auth import AccessClaims, JWTAuth
from fastapi import Depends, Request

from order.config import settings

auth = JWTAuth(Path(settings.jwt_public_key_path).read_text())
CurrentClaims = Annotated[AccessClaims, Depends(auth)]


def get_producer(request: Request) -> AIOKafkaProducer:
    return request.app.state.producer


Producer = Annotated[AIOKafkaProducer, Depends(get_producer)]
