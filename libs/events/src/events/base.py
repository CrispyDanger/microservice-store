from datetime import UTC, datetime
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class Event(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    order_id: str

    def to_kafka(self) -> tuple[bytes, bytes]:
        return self.order_id.encode(), self.model_dump_json().encode()
