# Orbit

[<span style="color: rgb(125, 133, 144);">https://github.com/tiangolo/full-stack-fastapi-template</span>](https://github.com/tiangolo/full-stack-fastapi-template)

tech debts:

Two small gaps worth knowing about, neither blocking:

1. `completed_at` **and** `timings` **are both** `null` — `queue.py` never actually sets `analysis.completed_at`, and there's no timing instrumentation at all despite your PRD's schema wanting both. Quick fix whenever you want it (a few lines in `run_analysis_job`), not urgent.
2. `facts_summary` **came back sparse for this repo** — no frameworks/datastores/ports detected, despite this template definitely using FastAPI + Postgres. Cause: `scanner.py`'s `_scan_python` only checks for `requirements.txt`/`pyproject.toml` at the **repo root**, and this template almost certainly nests its Python manifest under `backend/`. That's a real scanner coverage gap — and it's exactly why the agent correctly proposed nothing for db/queue services: no evidence, no invention. That's the "grounded generation" principle from your PRD's §7 working as designed, even though the underlying data was incomplete. Your PRD's own Phase 4 already anticipates broadening scanner coverage — this is that bucket, not an emergency.