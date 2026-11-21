from datetime import timedelta

from fastapi import APIRouter, Response, status

from order.publishing import oldest_unpublished_age

RELAY_LAG_LIMIT = timedelta(seconds=60)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/health/relay")
async def relay_health(response: Response) -> dict:
    age = await oldest_unpublished_age()
    stalled = age > RELAY_LAG_LIMIT
    if stalled:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "stalled" if stalled else "ok",
        "oldest_unpublished_seconds": int(age.total_seconds()),
    }
