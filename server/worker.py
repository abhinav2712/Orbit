import os
from redis import Redis
from rq import Worker, Queue

# ⚠️ Verify these var names against your `cache` service's "Access details"
# panel in Zerops — I can't see your live env vars, so this is my best guess
# at Zerops's naming convention (<hostname>_<field>). Adjust if they differ.
redis_conn = Redis(
    host=os.environ.get("cache_hostname", "localhost"),
    port=int(os.environ.get("cache_port", 6379)),
    password=os.environ.get("cache_password"),
)

if __name__ == "__main__":
    worker = Worker([Queue("default", connection=redis_conn)], connection=redis_conn)
    worker.work()
