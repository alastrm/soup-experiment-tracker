import hashlib
import hmac
import re
import secrets
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import APIError
from app.models import Batch, MetricEvent, Project, Run
from app.schemas import (
    MAX_SEQ, AcceptedEvent, BatchRequest, Event, EventWithSeq, KeyResponse,
    ProjectCreated, Receipt, RunDetail, RunList, RunResponse,
)


def new_key() -> tuple[str, bytes]:
    token = "soup_" + secrets.token_urlsafe(32)
    return token, hashlib.sha256(token.encode("ascii")).digest()


async def authenticate(session: AsyncSession, authorization: str | None, *, lock: str | None = None) -> Project:
    if authorization is None or not re.fullmatch(r"Bearer soup_[A-Za-z0-9_-]{43}", authorization):
        raise APIError("unauthorized")
    digest = hashlib.sha256(authorization[7:].encode("ascii")).digest()
    # Scalar ID avoids retaining a stale project ORM instance before locking.
    project_id = await session.scalar(select(Project.id).where(Project.key_hash == digest))
    if project_id is None:
        raise APIError("unauthorized")
    query = select(Project).where(Project.id == project_id)
    if lock is not None:
        query = query.with_for_update(read=lock == "share")
    project = await session.scalar(query.execution_options(populate_existing=True))
    if project is None or not hmac.compare_digest(project.key_hash, digest):
        raise APIError("unauthorized")
    return project


async def create_project(session: AsyncSession, name: str) -> ProjectCreated:
    token, digest = new_key()
    project = Project(name=name, key_hash=digest, key_version=1)
    session.add(project)
    await session.flush()
    return ProjectCreated(project=RunResponse.model_validate(project), api_key=token, key_version=1)


async def rotate_key(session: AsyncSession, authorization: str | None) -> KeyResponse:
    project = await authenticate(session, authorization, lock="update")
    token, digest = new_key()
    project.key_hash = digest
    project.key_version += 1
    await session.flush()
    return KeyResponse(api_key=token, key_version=project.key_version)


async def create_run(session: AsyncSession, authorization: str | None, name: str) -> RunResponse:
    project = await authenticate(session, authorization, lock="share")
    run = Run(project_id=project.id, name=name, last_seq=0)
    session.add(run)
    await session.flush()
    return RunResponse.model_validate(run)


async def scoped_run(session: AsyncSession, project_id: UUID, run_id: UUID, *, lock=False) -> Run:
    query = select(Run).where(Run.project_id == project_id, Run.id == run_id)
    if lock:
        query = query.with_for_update()
    run = await session.scalar(query.execution_options(populate_existing=True))
    if run is None:
        raise APIError("not_found")
    return run


async def list_runs(session: AsyncSession, authorization: str | None, limit: int, after: UUID | None) -> RunList:
    project = await authenticate(session, authorization)
    query = select(Run).where(Run.project_id == project.id)
    if after is not None:
        query = query.where(Run.id > after)
    rows = list((await session.scalars(query.order_by(Run.id).limit(limit + 1))).all())
    return RunList(runs=[RunResponse.model_validate(run) for run in rows[:limit]],
                   next_after=rows[limit - 1].id if len(rows) > limit else None)


async def run_detail(session: AsyncSession, authorization: str | None, run_id: UUID) -> RunDetail:
    project = await authenticate(session, authorization)
    run = await scoped_run(session, project.id, run_id)
    # PostgreSQL DISTINCT ON, with deterministic highest logical step/commit seq.
    query = (select(MetricEvent)
             .where(MetricEvent.project_id == project.id, MetricEvent.run_id == run.id,
                    MetricEvent.seq <= run.last_seq)
             .distinct(MetricEvent.metric)
             .order_by(MetricEvent.metric, MetricEvent.step.desc(), MetricEvent.seq.desc()))
    winners = list((await session.scalars(query)).all())
    # Sort in Python too: API order must not depend on database locale collation.
    winners.sort(key=lambda event: event.metric)
    return RunDetail(run=RunResponse.model_validate(run), last_seq=run.last_seq,
                     event_count=run.last_seq,
                     metrics=[EventWithSeq.model_validate(event) for event in winners])


async def ingest(session: AsyncSession, authorization: str | None, run_id: UUID, body: BatchRequest) -> Receipt:
    project = await authenticate(session, authorization, lock="share")
    run = await scoped_run(session, project.id, run_id, lock=True)
    canonical = body.canonical_bytes()
    digest = hashlib.sha256(canonical).digest()
    previous = await session.scalar(select(Batch).where(
        Batch.project_id == project.id, Batch.run_id == run.id, Batch.batch_id == body.batch_id))
    if previous is not None:
        if previous.digest != digest or previous.canonical != canonical:
            raise APIError("batch_conflict")
        return Receipt.model_validate(previous.receipt)

    events = list((await session.scalars(select(MetricEvent).where(
        MetricEvent.project_id == project.id, MetricEvent.run_id == run.id,
        MetricEvent.event_id.in_([event.event_id for event in body.events])))).all())
    known = {event.event_id: event for event in events}
    new_events = []
    for event in body.events:
        existing = known.get(event.event_id)
        if existing is None:
            new_events.append(event)
        elif Event.model_validate(existing).canonical_fields() != event.canonical_fields():
            raise APIError("event_conflict")

    if run.last_seq + len(new_events) > MAX_SEQ:
        raise APIError("cursor_exhausted")
    if new_events:
        names = set((await session.scalars(select(MetricEvent.metric).where(
            MetricEvent.project_id == project.id, MetricEvent.run_id == run.id)
            .distinct())).all())
        if len(names | {event.metric for event in new_events}) > 128:
            raise APIError("metric_limit")
    for event in new_events:
        run.last_seq += 1
        stored = MetricEvent(project_id=project.id, run_id=run.id, seq=run.last_seq,
                             **event.model_dump())
        session.add(stored)
        known[event.event_id] = stored
    receipt = Receipt(
        batch_id=body.batch_id,
        accepted=[AcceptedEvent(event_id=event.event_id, seq=known[event.event_id].seq) for event in body.events],
        inserted_count=len(new_events), deduplicated_count=len(body.events) - len(new_events),
        committed_seq=run.last_seq,
    )
    session.add(Batch(project_id=project.id, run_id=run.id, batch_id=body.batch_id,
                      canonical=canonical, digest=digest, receipt=receipt.model_dump(mode="json")))
    await session.flush()
    return receipt
