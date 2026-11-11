import json
import math
import re
import struct
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import Request
from pydantic import (
    BaseModel, BeforeValidator, ConfigDict, Field, ValidationError,
    field_serializer, field_validator, model_validator,
)

from app.errors import APIError

MAX_SEQ = 9_007_199_254_740_991
MAX_BODY = 262_144
UUID_PATTERN = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}")


def uuid4_string(value: object) -> UUID:
    if isinstance(value, UUID) and value.version == 4:
        return value
    if not isinstance(value, str) or not UUID_PATTERN.fullmatch(value):
        raise ValueError("UUIDv4 required")
    return UUID(value)


UUID4 = Annotated[UUID, BeforeValidator(uuid4_string)]
Name = Annotated[str, Field(strict=True, pattern=r"^[A-Za-z0-9][A-Za-z0-9 ._-]{0,99}$")]
Metric = Annotated[str, Field(strict=True, pattern=r"^[A-Za-z][A-Za-z0-9_.-]{0,63}$")]
Sequence = Annotated[int, Field(strict=True, ge=0, le=MAX_SEQ)]


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class NameRequest(Schema):
    name: Name


class EmptyRequest(Schema):
    pass


def utc_text(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


class Event(Schema):
    event_id: UUID4
    metric: Metric
    step: Sequence
    value: float
    occurred_at: datetime

    @field_validator("value", mode="before")
    @classmethod
    def finite_value(cls, value):
        if type(value) not in (int, float, Decimal):
            raise ValueError("JSON number required")
        try:
            number = float(value)
        except (ValueError, OverflowError):
            raise ValueError("Invalid binary64") from None
        if not math.isfinite(number) or abs(number) > 1e308:
            raise ValueError("Out of range")
        if number == 0 and value != 0:
            raise ValueError("Underflow")
        return 0.0 if number == 0 else number

    @field_validator("occurred_at", mode="before")
    @classmethod
    def utc_timestamp(cls, value):
        # ORM output is already validated/persisted; wire input must be exact UTC.
        if isinstance(value, datetime):
            parsed = value
        else:
            if not isinstance(value, str) or not re.fullmatch(
                r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z", value
            ):
                raise ValueError("UTC timestamp required")
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or not datetime(2000, 1, 1, tzinfo=UTC) <= parsed < datetime(2100, 1, 1, tzinfo=UTC):
            raise ValueError("Timestamp out of range")
        return parsed.astimezone(UTC)

    @field_serializer("occurred_at", when_used="json")
    def serialize_time(self, value):
        return utc_text(value)

    def canonical_fields(self) -> list:
        return [str(self.event_id), self.metric, self.step,
                struct.pack(">d", self.value).hex(), utc_text(self.occurred_at)]


class BatchRequest(Schema):
    batch_id: UUID4
    events: list[Event] = Field(min_length=1, max_length=250)

    @model_validator(mode="after")
    def unique_event_ids(self):
        if len({event.event_id for event in self.events}) != len(self.events):
            raise ValueError("Repeated event ID")
        return self

    def canonical_bytes(self) -> bytes:
        return json.dumps([1, [event.canonical_fields() for event in self.events]],
                          separators=(",", ":"), ensure_ascii=True).encode("utf-8")


class RunResponse(Schema):
    id: UUID4
    name: Name
    created_at: datetime

    @field_serializer("created_at", when_used="json")
    def serialize_created(self, value):
        return utc_text(value)


class ProjectCreated(Schema):
    project: RunResponse
    api_key: str
    key_version: int = Field(ge=1)


class KeyResponse(Schema):
    api_key: str
    key_version: int = Field(ge=1)


class RunList(Schema):
    runs: list[RunResponse] = Field(max_length=100)
    next_after: UUID4 | None


class EventWithSeq(Event):
    seq: Sequence


class RunDetail(Schema):
    run: RunResponse
    last_seq: Sequence
    event_count: Sequence
    metrics: list[EventWithSeq] = Field(max_length=128)


class AcceptedEvent(Schema):
    event_id: UUID4
    seq: Sequence


class Receipt(Schema):
    batch_id: UUID4
    accepted: list[AcceptedEvent] = Field(min_length=1, max_length=250)
    inserted_count: int = Field(ge=0, le=250)
    deduplicated_count: int = Field(ge=0, le=250)
    committed_seq: Sequence


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def reject_constant(_):
    raise ValueError("Nonstandard JSON number")


async def read_model[T: BaseModel](request: Request, model: type[T]) -> T:
    if request.headers.get("content-encoding", "identity").lower() != "identity":
        raise APIError("unsupported_media_type")
    media = request.headers.get("content-type", "").lower().replace(" ", "")
    if media not in ("application/json", "application/json;charset=utf-8"):
        raise APIError("unsupported_media_type")
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_BODY:
            raise APIError("payload_too_large")
        body.extend(chunk)
    try:
        data = json.loads(body.decode("utf-8"), parse_float=Decimal,
                          parse_constant=reject_constant, object_pairs_hook=unique_object)
    except (ValueError, UnicodeError, RecursionError):
        raise APIError("invalid_json") from None
    try:
        return model.model_validate(data)
    except ValidationError:
        raise APIError("validation_error") from None
