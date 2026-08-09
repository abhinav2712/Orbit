"""RQ queue setup + the analysis job: clone -> scan -> agent -> persist.
Publishes progress over Valkey pub/sub; events.py (SSE) subscribes per analysis id."""

from __future__ import annotations

import json
import traceback

from redis import Redis
from rq import Queue

from app.deps import get_cached_result, get_redis, get_sessionmaker, set_cached_result
from app.models import Analysis, AnalysisStatus
from engine import artifacts
from engine.agent import run_agent
from engine.cloner import ClonerError, clone_repo, cleanup as cleanup_clone
from engine.scanner import scan_repo
from app.deps import (
    get_cached_result,
    get_redis,
    get_rq_redis,
    get_sessionmaker,
    set_cached_result,
)

JOB_TIMEOUT_SECONDS = 300  # 5 min wall-clock cap, per PRD F8


def get_queue() -> Queue:
    return Queue(
        "orbit-analyses", connection=get_rq_redis(), default_timeout=JOB_TIMEOUT_SECONDS
    )


def enqueue_analysis(analysis_id: str) -> None:
    get_queue().enqueue(run_analysis_job, analysis_id, job_timeout=JOB_TIMEOUT_SECONDS)


def _publish(redis: Redis, analysis_id: str, status: str, message: str) -> None:
    redis.publish(
        f"analysis-events:{analysis_id}",
        json.dumps({"status": status, "message": message}),
    )


def run_analysis_job(analysis_id: str) -> None:
    """Runs inside the RQ worker process. Never raises — always ends in done/failed."""
    redis = get_redis()
    session = get_sessionmaker()()
    cloned = None
    try:
        analysis = session.get(Analysis, analysis_id)
        if not analysis:
            return

        analysis.status = AnalysisStatus.cloning
        session.commit()
        _publish(redis, analysis_id, "cloning", f"Cloning {analysis.repo_url}...")

        cloned = clone_repo(analysis.repo_url)
        analysis.head_sha = cloned.head_sha
        session.commit()

        cached = get_cached_result(analysis.repo_url, cloned.head_sha)
        if cached:
            _publish(
                redis,
                analysis_id,
                "done",
                "Found a cached analysis for this exact commit.",
            )
            analysis.facts = cached["facts"]
            analysis.services = cached["services"]
            analysis.zerops_yaml = cached["zerops_yaml"]
            analysis.checklist = cached["checklist"]
            analysis.status = AnalysisStatus.done
            session.commit()
            return

        analysis.status = AnalysisStatus.scanning
        session.commit()
        _publish(
            redis,
            analysis_id,
            "scanning",
            "Scanning repo for languages, frameworks, ports...",
        )
        facts = scan_repo(cloned.path, analysis.repo_url, cloned.head_sha)

        analysis.status = AnalysisStatus.reasoning
        session.commit()
        _publish(
            redis,
            analysis_id,
            "reasoning",
            "Reasoning over Facts with the architect agent...",
        )

        def on_progress(msg: str) -> None:
            _publish(redis, analysis_id, "reasoning", msg)

        ctx = run_agent(facts.model_dump(), cloned.path, on_progress=on_progress)

        analysis.status = AnalysisStatus.validating
        session.commit()
        _publish(
            redis, analysis_id, "validating", "Validating generated zerops.yaml..."
        )

        analysis.facts = facts.model_dump()
        analysis.services = ctx.services
        analysis.zerops_yaml = ctx.zerops_yaml
        analysis.checklist = ctx.checklist
        analysis.status = AnalysisStatus.done
        session.commit()

        artifacts.upload_analysis_artifacts(
            analysis_id, facts.model_dump(), ctx.zerops_yaml, ctx.checklist
        )

        if ctx.zerops_yaml and ctx.yaml_valid:
            set_cached_result(
                analysis.repo_url,
                cloned.head_sha,
                {
                    "facts": analysis.facts,
                    "services": analysis.services,
                    "zerops_yaml": analysis.zerops_yaml,
                    "checklist": analysis.checklist,
                },
            )

        _publish(redis, analysis_id, "done", "Analysis complete.")

    except ClonerError as e:
        _fail(session, redis, analysis_id, str(e))
    except Exception:
        _fail(session, redis, analysis_id, "Unexpected error during analysis.")
        traceback.print_exc()
    finally:
        if cloned:
            cleanup_clone(cloned)
        session.close()


def _fail(session, redis: Redis, analysis_id: str, reason: str) -> None:
    analysis = session.get(Analysis, analysis_id)
    if analysis:
        analysis.status = AnalysisStatus.failed
        analysis.error = reason
        session.commit()
    _publish(redis, analysis_id, "failed", reason)
