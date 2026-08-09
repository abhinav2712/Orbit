"""SSE progress stream, backed by Valkey pub/sub. One channel per analysis id."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.deps import get_redis

router = APIRouter(prefix="/api/analyses", tags=["events"])


@router.get("/{analysis_id}/events")
async def stream_events(analysis_id: str):
    async def event_generator():
        redis = get_redis()
        pubsub = redis.pubsub()
        pubsub.subscribe(f"analysis-events:{analysis_id}")
        try:
            while True:
                message = pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if message:
                    data = message["data"]
                    yield f"data: {data}\n\n"
                    if json.loads(data).get("status") in ("done", "failed"):
                        break
                await asyncio.sleep(0.1)
        finally:
            pubsub.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream")
