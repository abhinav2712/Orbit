"""Shared clients: Postgres, Valkey, object storage. Rate-limit + result-cache helpers."""

from __future__ import annotations

import json
import os
from functools import lru_cache

import boto3
from botocore.config import Config
from redis import Redis
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL not set — check zerops.yml envVariables")
    return url.replace("postgresql://", "postgresql+psycopg://", 1)


@lru_cache
def get_redis() -> Redis:
    url = os.environ.get("REDIS_URL")
    if not url:
        raise RuntimeError("REDIS_URL not set — check zerops.yml envVariables")
    return Redis.from_url(url, decode_responses=True)


@lru_cache
def get_engine():
    return create_engine(_database_url(), pool_pre_ping=True)


@lru_cache
def get_sessionmaker() -> sessionmaker:
    return sessionmaker(bind=get_engine())


def get_db() -> Session:
    db = get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()


@lru_cache
def get_redis() -> Redis:
    # Verify these against `cache`'s Access Details panel in Zerops.
    host = os.environ.get("cache_hostname", "localhost")
    port = int(os.environ.get("cache_port", 6379))
    password = os.environ.get("cache_password")
    return Redis(host=host, port=port, password=password, decode_responses=True)



@lru_cache
def get_object_storage():
    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("S3_ENDPOINT_URL"),
        aws_access_key_id=os.environ.get("S3_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("S3_SECRET_ACCESS_KEY"),
        region_name=os.environ.get("S3_REGION", "us-east-1"),
        config=Config(s3={"addressing_style": "path"}),
    )


RATE_LIMIT_MAX = 5
RATE_LIMIT_WINDOW_SECONDS = 3600


def check_rate_limit(ip: str) -> bool:
    r = get_redis()
    key = f"ratelimit:{ip}"
    count = r.incr(key)
    if count == 1:
        r.expire(key, RATE_LIMIT_WINDOW_SECONDS)
    return count <= RATE_LIMIT_MAX


CACHE_TTL_SECONDS = 24 * 3600


def get_cached_result(repo_url: str, head_sha: str) -> dict | None:
    raw = get_redis().get(f"analysis-cache:{repo_url}:{head_sha}")
    return json.loads(raw) if raw else None


def set_cached_result(repo_url: str, head_sha: str, result: dict) -> None:
    get_redis().setex(
        f"analysis-cache:{repo_url}:{head_sha}", CACHE_TTL_SECONDS, json.dumps(result)
    )
