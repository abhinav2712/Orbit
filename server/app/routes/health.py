"""GET /healthz — checks db + cache, reports worker liveness from its heartbeat key."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.deps import get_db, get_redis

router = APIRouter()

WORKER_HEARTBEAT_KEY = "worker:heartbeat"
WORKER_STALE_AFTER_SECONDS = 90


@router.get("/healthz")
def healthz(db: Session = Depends(get_db)):
    checks = {}
    try:
        db.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as e:
        checks["db"] = f"error: {e}"

    try:
        redis = get_redis()
        redis.ping()
        checks["cache"] = "ok"
        last_beat = redis.get(WORKER_HEARTBEAT_KEY)
        checks["worker"] = (
            "ok"
            if last_beat
            and (time.time() - float(last_beat)) < WORKER_STALE_AFTER_SECONDS
            else "stale or not running"
        )
    except Exception as e:
        checks["cache"] = f"error: {e}"
        checks["worker"] = "unknown"

    healthy = all(v == "ok" for v in checks.values())
    return {"status": "ok" if healthy else "degraded", "checks": checks}
