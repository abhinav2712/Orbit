"""RQ worker entrypoint. Listens on 'orbit-analyses' and writes a heartbeat every 30s
so api's /healthz can report worker liveness."""

from __future__ import annotations

import threading
import time

from rq import Worker

from app.deps import get_redis
from app.queue import get_queue

HEARTBEAT_KEY = "worker:heartbeat"
HEARTBEAT_INTERVAL_SECONDS = 30


def _heartbeat_loop() -> None:
    redis = get_redis()
    while True:
        redis.setex(
            HEARTBEAT_KEY, HEARTBEAT_INTERVAL_SECONDS * 2, str(int(time.time()))
        )
        time.sleep(HEARTBEAT_INTERVAL_SECONDS)


if __name__ == "__main__":
    threading.Thread(target=_heartbeat_loop, daemon=True).start()
    worker = Worker([get_queue()], connection=get_redis())
    worker.work()
