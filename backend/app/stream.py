"""Durable DB replay with no broadcast queue or long-lived DB session."""
import asyncio
import json
from uuid import UUID

from sqlalchemy import select
from starlette.responses import Response

from app.db import Database
from app.errors import APIError, error_response
from app.models import MetricEvent, Project
from app.schemas import EventWithSeq, MAX_SEQ
from app.services import scoped_run


def parse_cursor(value: str | None) -> int:
    if value is None:
        return 0
    if not value.isascii() or not value.isdigit() or len(value) > 16 or (len(value) > 1 and value[0] == "0"):
        raise APIError("validation_error")
    cursor = int(value)
    if cursor > MAX_SEQ:
        raise APIError("validation_error")
    return cursor


async def replay_page(db: Database, project_id: UUID, run_id: UUID, cursor: int):
    async with db.transaction(snapshot=True) as session:
        run = await scoped_run(session, project_id, run_id)
        high_water = run.last_seq
        rows = (await session.scalars(select(MetricEvent).where(
            MetricEvent.project_id == project_id, MetricEvent.run_id == run_id,
            MetricEvent.seq > cursor, MetricEvent.seq <= high_water,
        ).order_by(MetricEvent.seq).limit(250))).all()
        events = [EventWithSeq.model_validate(row) for row in rows]
    return high_water, events


class StreamSlots:
    def __init__(self, limit=100):
        self.active = 0
        self.limit = limit


class DurableSSE(Response):
    media_type = "text/event-stream"
    send_timeout = 5.0
    key_interval = 1.0
    key_timeout = 1.0

    def __init__(self, db, slots, project, run_id, cursor):
        super().__init__(headers={"Cache-Control": "no-store, no-transform", "X-Accel-Buffering": "no"})
        self.raw_headers = [(k, v) for k, v in self.raw_headers if k != b"content-length"]
        self.db, self.slots = db, slots
        self.project_id, self.key_hash, self.key_version = project.id, project.key_hash, project.key_version
        self.run_id, self.cursor = run_id, cursor
        self.revoked = False
        self.sending = False

    async def __call__(self, scope, receive, send):
        # Synchronous admission has no await/race within one event loop. It is
        # only a resource cap; PostgreSQL locks remain the correctness boundary.
        if self.slots.active >= self.slots.limit:
            return await error_response("temporarily_unavailable")(scope, receive, send)
        self.slots.active += 1
        tasks = []

        async def bounded_send(message):
            self.sending = True
            try:
                async with asyncio.timeout(self.send_timeout):
                    await send(message)
            finally:
                self.sending = False

        async def frame(event, data, seq=None):
            payload = f"event: {event}\n" + (f"id: {seq}\n" if seq is not None else "")
            payload += "data: " + json.dumps(data, separators=(",", ":"), allow_nan=False) + "\n\n"
            encoded = payload.encode()
            if len(encoded) > 4096:
                raise RuntimeError("SSE frame exceeds bound")
            await bounded_send({"type": "http.response.body", "body": encoded, "more_body": True})

        async def produce():
            await bounded_send({"type": "http.response.start", "status": 200, "headers": self.raw_headers})
            last_marker = -1
            heartbeat = asyncio.get_running_loop().time()
            while True:
                high, events = await replay_page(self.db, self.project_id, self.run_id, self.cursor)
                for event in events:
                    await frame("metric", event.model_dump(mode="json"), event.seq)
                    self.cursor = event.seq
                if self.cursor == high and high != last_marker:
                    await frame("caught_up", {"cursor": high})
                    last_marker = high
                now = asyncio.get_running_loop().time()
                if now - heartbeat >= 10:
                    await bounded_send({"type": "http.response.body", "body": b": heartbeat\n\n", "more_body": True})
                    heartbeat = now
                if self.cursor == high:
                    await asyncio.sleep(0.25)

        async def watch_key():
            tick = asyncio.get_running_loop().time()
            while True:
                tick += self.key_interval
                await asyncio.sleep(max(0, tick - asyncio.get_running_loop().time()))
                async with asyncio.timeout(self.key_timeout):
                    async with self.db.sessions() as session:
                        valid = await session.scalar(select(Project.id).where(
                            Project.id == self.project_id, Project.key_hash == self.key_hash,
                            Project.key_version == self.key_version))
                if valid is None:
                    self.revoked = True
                    return

        async def disconnect():
            while (await receive())["type"] != "http.disconnect":
                pass

        try:
            producer = asyncio.create_task(produce())
            watcher = asyncio.create_task(watch_key())
            reader = asyncio.create_task(disconnect())
            tasks = [producer, watcher, reader]
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            blocked = self.sending
            producer_failed = producer in done and not producer.cancelled() and producer.exception() is not None
            peer_disconnected = reader in done
            for task in tasks:
                task.cancel()
            # Await cleanup before returning the admission slot/connections.
            await asyncio.gather(*tasks, return_exceptions=True)
            if self.revoked and not blocked and not producer_failed and not peer_disconnected:
                await frame("auth_expired", {"code": "unauthorized"})
            # Re-entering a stalled/failed send for EOF costs another timeout.
            # Returning an incomplete response closes the transport; the client
            # recovers from its last applied cursor, including any partial frame.
            if not blocked and not producer_failed and not peer_disconnected:
                await bounded_send({"type": "http.response.body", "body": b"", "more_body": False})
        except (OSError, TimeoutError):
            pass  # EOF + durable replay is the recovery protocol.
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            self.slots.active -= 1
