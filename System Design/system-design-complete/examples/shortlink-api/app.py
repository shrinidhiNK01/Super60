"""A deliberately small, runnable learning API.

It demonstrates validation, request IDs, idempotent create, durable SQLite
storage, expiry, and safe redirect headers. SQLite is suitable for this local
single-instance lab only. The documentation explains how to replace it with a
managed relational database before scaling replicas.
"""

import hashlib
import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Iterator
from urllib.parse import urlparse

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field


# Keep the file outside the image's application directory so a mounted volume
# can persist it during local Docker runs. Production should use a managed DB.
DATABASE_PATH = os.getenv("DATABASE_PATH", "/data/shortlink.db")

# The alphabet deliberately avoids confusing characters such as 0/O and 1/l.
ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

app = FastAPI(title="Shortlink learning API", version="1.0.0")


class CreateLinkRequest(BaseModel):
    """The public input contract for link creation."""

    destination: str = Field(min_length=8, max_length=2048)
    expires_at: datetime | None = None


class LinkResponse(BaseModel):
    """The stable response returned for both original and replayed requests."""

    code: str
    destination: str
    expires_at: datetime | None


@contextmanager
def database() -> Iterator[sqlite3.Connection]:
    """Open one SQLite connection for a short operation and close it reliably."""

    connection = sqlite3.connect(DATABASE_PATH, timeout=5, isolation_level=None)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


def initialise_database() -> None:
    """Create the source-of-truth and idempotency tables if this is first boot."""

    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    with database() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS links (
              code TEXT PRIMARY KEY,
              destination TEXT NOT NULL,
              expires_at TEXT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS idempotency_keys (
              key TEXT PRIMARY KEY,
              request_hash TEXT NOT NULL,
              response_json TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            """
        )


@app.on_event("startup")
def on_startup() -> None:
    """Run schema creation before the process says it is ready."""

    initialise_database()


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Assign/forward a correlation ID without trusting it as an auth credential."""

    request_id = request.headers.get("X-Request-Id", secrets.token_hex(12))
    response: Response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    return response


def validate_destination(destination: str) -> None:
    """Allow only ordinary HTTP(S) destinations for this teaching example."""

    parsed = urlparse(destination)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=422, detail="destination must be an absolute http(s) URL")


def canonical_request_hash(payload: CreateLinkRequest) -> str:
    """Create a stable hash so one idempotency key cannot mean two requests."""

    body = json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def new_code() -> str:
    """Generate a short unpredictable code; the DB primary key handles collisions."""

    return "".join(secrets.choice(ALPHABET) for _ in range(8))


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Cheap health endpoint; it checks process readiness, not every dependency."""

    return {"status": "ok"}


@app.post("/v1/links", response_model=LinkResponse, status_code=201)
def create_link(
    payload: CreateLinkRequest,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=16, max_length=128),
) -> LinkResponse:
    """Create one link, returning the saved response when a client safely retries."""

    validate_destination(payload.destination)
    if payload.expires_at and payload.expires_at.tzinfo is None:
        raise HTTPException(status_code=422, detail="expires_at must include a timezone")
    if payload.expires_at and payload.expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=422, detail="expires_at must be in the future")

    request_hash = canonical_request_hash(payload)
    now = datetime.now(UTC).isoformat()
    expires_at = payload.expires_at.astimezone(UTC).isoformat() if payload.expires_at else None

    with database() as connection:
        # IMMEDIATE obtains SQLite's write lock before checking/inserting, which
        # makes the check-and-create sequence atomic for this one local database.
        connection.execute("BEGIN IMMEDIATE")
        previous = connection.execute(
            "SELECT request_hash, response_json FROM idempotency_keys WHERE key = ?",
            (idempotency_key,),
        ).fetchone()
        if previous:
            if previous["request_hash"] != request_hash:
                connection.execute("ROLLBACK")
                raise HTTPException(status_code=409, detail="idempotency key was reused with another request")
            connection.execute("COMMIT")
            return LinkResponse.model_validate_json(previous["response_json"])

        # Collision is very unlikely, but the primary key—not probability—is the
        # final uniqueness guard. Retry a bounded number of generated codes.
        for _ in range(5):
            code = new_code()
            try:
                connection.execute(
                    "INSERT INTO links (code, destination, expires_at, created_at) VALUES (?, ?, ?, ?)",
                    (code, payload.destination, expires_at, now),
                )
                break
            except sqlite3.IntegrityError:
                continue
        else:
            connection.execute("ROLLBACK")
            raise HTTPException(status_code=503, detail="could not allocate a link code; retry later")

        response = LinkResponse(code=code, destination=payload.destination, expires_at=payload.expires_at)
        connection.execute(
            "INSERT INTO idempotency_keys (key, request_hash, response_json, created_at) VALUES (?, ?, ?, ?)",
            (idempotency_key, request_hash, response.model_dump_json(), now),
        )
        connection.execute("COMMIT")
        return response


@app.get("/{code}", include_in_schema=False)
def redirect_to_destination(code: str) -> RedirectResponse:
    """Look up a valid link and return a temporary redirect without caching private state."""

    with database() as connection:
        row = connection.execute(
            "SELECT destination, expires_at FROM links WHERE code = ?", (code,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="link not found")
    if row["expires_at"] and datetime.fromisoformat(row["expires_at"]) <= datetime.now(UTC):
        raise HTTPException(status_code=410, detail="link has expired")
    response = RedirectResponse(url=row["destination"], status_code=307)
    response.headers["Cache-Control"] = "no-store"
    return response
