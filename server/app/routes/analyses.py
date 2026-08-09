"""POST /api/analyses, GET /api/analyses/{id_or_slug}, gallery, checklist toggle."""

from __future__ import annotations

import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.deps import check_rate_limit, get_db
from app.models import Analysis, AnalysisStatus, ChecklistState
from app.queue import enqueue_analysis
from app.schemas import AnalysisResult, CreateAnalysisRequest, CreateAnalysisResponse
from engine.cloner import ClonerError, check_repo_size, parse_github_url

router = APIRouter(prefix="/api/analyses", tags=["analyses"])


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


@router.post("", status_code=202, response_model=CreateAnalysisResponse)
def create_analysis(
    body: CreateAnalysisRequest, request: Request, db: Session = Depends(get_db)
):
    ip = _client_ip(request)
    if not check_rate_limit(ip):
        raise HTTPException(429, "Rate limit exceeded — try again in an hour.")

    repo_url = str(body.repo_url)
    try:
        owner, name = parse_github_url(repo_url)
        check_repo_size(owner, name)
    except ClonerError as e:
        raise HTTPException(400, str(e))

    slug = secrets.token_urlsafe(6)
    analysis = Analysis(slug=slug, repo_url=repo_url, status=AnalysisStatus.queued)
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    enqueue_analysis(str(analysis.id))
    return CreateAnalysisResponse(id=str(analysis.id), slug=slug)


@router.get("/{id_or_slug}", response_model=AnalysisResult)
def get_analysis(id_or_slug: str, db: Session = Depends(get_db)):
    analysis = db.get(Analysis, id_or_slug) if _is_uuid(id_or_slug) else None
    if not analysis:
        analysis = db.query(Analysis).filter(Analysis.slug == id_or_slug).first()
    if not analysis:
        raise HTTPException(404, "Analysis not found.")

    return AnalysisResult(
        id=str(analysis.id),
        slug=analysis.slug,
        status=analysis.status.value,
        error=analysis.error,
        facts_summary=analysis.facts,
        services=analysis.services,
        zerops_yaml=analysis.zerops_yaml,
        yaml_valid=bool(analysis.zerops_yaml),
        checklist=analysis.checklist,
        timings=analysis.timings,
        created_at=analysis.created_at,
        completed_at=analysis.completed_at,
    )


@router.get("")
def list_public_analyses(
    public: int = 1, limit: int = 20, db: Session = Depends(get_db)
):
    q = db.query(Analysis).filter(Analysis.status == AnalysisStatus.done)
    if public:
        q = q.filter(Analysis.is_public.is_(True))
    rows = q.order_by(Analysis.created_at.desc()).limit(limit).all()
    return [
        {"slug": a.slug, "repo_url": a.repo_url, "created_at": a.created_at}
        for a in rows
    ]


@router.post("/{analysis_id}/checklist/{step_id}/toggle")
def toggle_checklist_step(
    analysis_id: str, step_id: str, db: Session = Depends(get_db)
):
    state = db.get(ChecklistState, (analysis_id, step_id))
    if not state:
        state = ChecklistState(analysis_id=analysis_id, step_id=step_id, checked=True)
        db.add(state)
    else:
        state.checked = not state.checked
    db.commit()
    return {"checked": state.checked}


@router.delete("/{id_or_slug}")
def delete_analysis(id_or_slug: str, db: Session = Depends(get_db)):
    analysis = db.get(Analysis, id_or_slug) if _is_uuid(id_or_slug) else None
    if not analysis:
        analysis = db.query(Analysis).filter(Analysis.slug == id_or_slug).first()
    if not analysis:
        raise HTTPException(404, "Analysis not found.")
    db.query(ChecklistState).filter(ChecklistState.analysis_id == analysis.id).delete()
    db.delete(analysis)
    db.commit()
    return {"deleted": True}
