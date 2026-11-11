import os
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, TimeoutError as SQLTimeoutError
from starlette.exceptions import HTTPException
from starlette.middleware.cors import CORSMiddleware

from app import services
from app.db import Database
from app.errors import APIError, error_response
from app.schemas import (
    UUID4, BatchRequest, EmptyRequest, KeyResponse, NameRequest,
    ProjectCreated, Receipt, RunDetail, RunList, RunResponse, read_model,
)
from app.stream import DurableSSE, StreamSlots, parse_cursor


class ResponsePolicy:
    """Cover framework/DB errors too; never let a traceback log request data."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        started = False

        async def private_send(message):
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
                headers = [(key, value) for key, value in message.get("headers", [])
                           if key.lower() not in (b"cache-control", b"vary")]
                streaming = any(k == b"content-type" and v.startswith(b"text/event-stream") for k, v in headers)
                headers.extend([(b"cache-control", b"no-store, no-transform" if streaming else b"no-store"),
                                (b"vary", b"Origin, Authorization")])
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, private_send)
        except Exception:
            # FastAPI's ServerErrorMiddleware re-raises after our sanitized 500.
            if not started:
                await error_response("internal_error")(scope, receive, private_send)


def create_app(database: Database | None = None):
    database = database or Database()

    @asynccontextmanager
    async def lifespan(_):
        yield
        await database.engine.dispose()

    api = FastAPI(title="Soup experiment tracker", lifespan=lifespan)
    api.state.db = database
    api.state.streams = StreamSlots()

    @api.exception_handler(APIError)
    async def domain_error(_, exc):
        return error_response(exc.code)

    @api.exception_handler(RequestValidationError)
    async def invalid_request(_, __):
        return error_response("validation_error")

    @api.exception_handler(HTTPException)
    async def http_error(_, exc):
        return error_response({404: "not_found", 405: "method_not_allowed", 401: "unauthorized"}
                              .get(exc.status_code, "validation_error"))

    @api.exception_handler(DBAPIError)
    @api.exception_handler(SQLTimeoutError)
    @api.exception_handler(TimeoutError)
    async def database_error(_, exc):
        if isinstance(exc, DBAPIError):
            state = getattr(exc.orig, "sqlstate", "") or ""
            transient = (exc.connection_invalidated or state.startswith("08")
                         or state in {"40001", "40P01", "55P03", "57014", "53300", "57P01"})
            return error_response("temporarily_unavailable" if transient else "internal_error")
        return error_response("temporarily_unavailable")

    @api.exception_handler(Exception)
    async def unexpected_error(_, __):
        return error_response("internal_error")

    @api.get("/health")
    async def health():
        async with database.transaction() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ok"}

    @api.post("/projects", status_code=201, response_model=ProjectCreated)
    async def project_create(request: Request):
        body = await read_model(request, NameRequest)
        async with database.transaction() as session:
            result = await services.create_project(session, body.name)
        return result

    @api.post("/projects/key/rotate", response_model=KeyResponse)
    async def project_rotate(request: Request):
        await read_model(request, EmptyRequest)
        async with database.transaction() as session:
            result = await services.rotate_key(session, request.headers.get("authorization"))
        return result

    @api.post("/runs", status_code=201, response_model=RunResponse)
    async def run_create(request: Request):
        body = await read_model(request, NameRequest)
        async with database.transaction() as session:
            result = await services.create_run(session, request.headers.get("authorization"), body.name)
        return result

    @api.get("/runs", response_model=RunList)
    async def runs_list(request: Request, limit: Annotated[int, Query(ge=1, le=100)] = 50,
                        after: UUID4 | None = None):
        async with database.transaction() as session:
            result = await services.list_runs(session, request.headers.get("authorization"), limit, after)
        return result

    @api.get("/runs/{run_id}", response_model=RunDetail)
    async def run_get(request: Request, run_id: UUID4):
        async with database.transaction(snapshot=True) as session:
            result = await services.run_detail(session, request.headers.get("authorization"), run_id)
        return result

    @api.post("/runs/{run_id}/metrics", response_model=Receipt)
    async def metrics_post(request: Request, run_id: UUID4):
        body = await read_model(request, BatchRequest)
        async with database.transaction() as session:
            result = await services.ingest(session, request.headers.get("authorization"), run_id, body)
        return result

    @api.get("/runs/{run_id}/events")
    async def events_get(request: Request, run_id: UUID4):
        async with database.transaction(snapshot=True) as session:
            project = await services.authenticate(session, request.headers.get("authorization"))
            run = await services.scoped_run(session, project.id, run_id)
            cursor = parse_cursor(request.headers.get("last-event-id"))
            if cursor > run.last_seq:
                raise APIError("cursor_ahead")
        return DurableSSE(database, api.state.streams, project, run_id, cursor)

    cors = CORSMiddleware(api, allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
                         allow_credentials=False, allow_methods=["GET", "POST", "OPTIONS"],
                         allow_headers=["Authorization", "Content-Type", "Accept", "Last-Event-ID"],
                         expose_headers=["Retry-After"])
    app = ResponsePolicy(cors)
    app.state = api.state
    return app
