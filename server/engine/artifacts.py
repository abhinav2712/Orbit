"""Upload analysis artifacts (yaml, facts report, checklist) to Zerops object storage."""

from __future__ import annotations

import json

from app.deps import get_object_storage

import os
BUCKET = os.environ.get("S3_BUCKET_NAME", "orbit-artifacts")


def upload_analysis_artifacts(
    analysis_id: str, facts: dict, zerops_yaml: str | None, checklist: list | None
) -> dict:
    s3 = get_object_storage()
    urls = {}

    def _put(key: str, body: str, content_type: str) -> str:
        s3.put_object(
            Bucket=BUCKET, Key=key, Body=body.encode("utf-8"), ContentType=content_type
        )
        return key

    urls["report_json"] = _put(
        f"{analysis_id}/report.json", json.dumps(facts, indent=2), "application/json"
    )
    if zerops_yaml:
        urls["yaml"] = _put(f"{analysis_id}/zerops.yaml", zerops_yaml, "text/yaml")
    if checklist:
        urls["checklist_json"] = _put(
            f"{analysis_id}/checklist.json",
            json.dumps(checklist, indent=2),
            "application/json",
        )

    return urls
