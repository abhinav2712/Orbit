"""Deterministic static analysis — no LLM calls. Every fact carries file:line evidence."""

from __future__ import annotations

import json
import os
import re
from typing import Iterable

from pydantic import BaseModel

IGNORE_DIRS = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    "dist",
    "build",
    ".next",
    "target",
    "vendor",
    ".turbo",
}
MAX_FILE_BYTES = 512 * 1024


class Evidence(BaseModel):
    file: str
    line: int
    snippet: str


class Fact(BaseModel):
    value: str
    evidence: list[Evidence] = []


class PortFact(BaseModel):
    port: int
    evidence: list[Evidence] = []


class Facts(BaseModel):
    repo_url: str
    head_sha: str
    languages: list[Fact] = []
    frameworks: list[Fact] = []
    ports: list[PortFact] = []
    datastores: list[Fact] = []
    queues: list[Fact] = []
    storage: list[Fact] = []
    env_vars: list[Fact] = []
    has_dockerfile: bool = False
    static_output_dir: str | None = None
    build_commands: list[Fact] = []


PY_FRAMEWORK_PACKAGES = {"fastapi": "fastapi", "flask": "flask", "django": "django"}
PY_QUEUE_PACKAGES = {"celery": "celery", "rq": "rq"}
PY_DATASTORE_PACKAGES = {
    "psycopg2": "postgresql",
    "psycopg2-binary": "postgresql",
    "psycopg": "postgresql",
    "asyncpg": "postgresql",
    "pymongo": "mongodb",
    "motor": "mongodb",
    "redis": "redis/valkey",
}
PY_STORAGE_PACKAGES = {
    "boto3": "s3-compatible object storage sdk",
    "minio": "s3-compatible object storage sdk",
}

NODE_FRAMEWORK_PACKAGES = {
    "express": "express",
    "fastify": "fastify",
    "next": "next.js",
    "nuxt": "nuxt",
    "vite": "vite",
    "react": "react",
    "vue": "vue",
    "@nestjs/core": "nestjs",
}
NODE_QUEUE_PACKAGES = {"bullmq": "bullmq"}
NODE_DATASTORE_PACKAGES = {
    "pg": "postgresql",
    "mysql2": "mysql",
    "mongoose": "mongodb",
    "mongodb": "mongodb",
    "redis": "redis/valkey",
    "ioredis": "redis/valkey",
}
NODE_STORAGE_PACKAGES = {
    "aws-sdk": "s3-compatible object storage sdk",
    "@aws-sdk/client-s3": "s3-compatible object storage sdk",
}

ENV_VAR_PATTERNS = [
    re.compile(r"os\.environ(?:\.get)?\(\s*[\"']([A-Z_][A-Z0-9_]*)[\"']"),
    re.compile(r"os\.getenv\(\s*[\"']([A-Z_][A-Z0-9_]*)[\"']"),
    re.compile(r"process\.env\.([A-Z_][A-Z0-9_]*)"),
]
PORT_PATTERNS = [
    re.compile(r"uvicorn\.run\([^)]*port\s*=\s*(\d{2,5})"),
    re.compile(r"app\.run\([^)]*port\s*=\s*(\d{2,5})"),
    re.compile(r"\.listen\(\s*(\d{2,5})"),
    re.compile(r"EXPOSE\s+(\d{2,5})", re.IGNORECASE),
]


def _iter_source_files(root: str) -> Iterable[str]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames if d not in IGNORE_DIRS and not d.startswith(".")
        ]
        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            try:
                if os.path.getsize(fpath) > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            yield fpath


def _rel(root: str, path: str) -> str:
    return os.path.relpath(path, root)


def _scan_env_vars_and_ports(
    root: str,
) -> tuple[dict[str, list[Evidence]], dict[int, list[Evidence]]]:
    env_hits: dict[str, list[Evidence]] = {}
    port_hits: dict[int, list[Evidence]] = {}
    for fpath in _iter_source_files(root):
        if not fpath.endswith(
            (".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", "Dockerfile")
        ):
            continue
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
                lines = fh.readlines()
        except OSError:
            continue
        for i, line in enumerate(lines, start=1):
            for pat in ENV_VAR_PATTERNS:
                for m in pat.finditer(line):
                    ev = Evidence(
                        file=_rel(root, fpath), line=i, snippet=line.strip()[:200]
                    )
                    env_hits.setdefault(m.group(1), []).append(ev)
            for pat in PORT_PATTERNS:
                for m in pat.finditer(line):
                    ev = Evidence(
                        file=_rel(root, fpath), line=i, snippet=line.strip()[:200]
                    )
                    port_hits.setdefault(int(m.group(1)), []).append(ev)
    return env_hits, port_hits


def _scan_python(root: str, facts: Facts) -> None:
    req_path = os.path.join(root, "requirements.txt")
    pyproject_path = os.path.join(root, "pyproject.toml")
    if os.path.exists(req_path):
        manifest_path, text = (
            req_path,
            open(req_path, encoding="utf-8", errors="ignore").read(),
        )
    elif os.path.exists(pyproject_path):
        manifest_path, text = (
            pyproject_path,
            open(pyproject_path, encoding="utf-8", errors="ignore").read(),
        )
    else:
        return

    rel = _rel(root, manifest_path)
    facts.languages.append(
        Fact(value="python", evidence=[Evidence(file=rel, line=1, snippet="found")])
    )
    lowered = text.lower()

    for pkg, label in PY_FRAMEWORK_PACKAGES.items():
        if pkg in lowered:
            facts.frameworks.append(
                Fact(value=label, evidence=[Evidence(file=rel, line=1, snippet=pkg)])
            )
    for pkg, label in PY_DATASTORE_PACKAGES.items():
        if pkg in lowered:
            facts.datastores.append(
                Fact(value=label, evidence=[Evidence(file=rel, line=1, snippet=pkg)])
            )
    for pkg, label in PY_STORAGE_PACKAGES.items():
        if pkg in lowered:
            facts.storage.append(
                Fact(value=label, evidence=[Evidence(file=rel, line=1, snippet=pkg)])
            )
    for pkg, label in PY_QUEUE_PACKAGES.items():
        if pkg in lowered:
            facts.queues.append(
                Fact(value=label, evidence=[Evidence(file=rel, line=1, snippet=pkg)])
            )


def _scan_node(root: str, facts: Facts) -> None:
    pkg_path = os.path.join(root, "package.json")
    if not os.path.exists(pkg_path):
        return
    try:
        data = json.loads(open(pkg_path, encoding="utf-8", errors="ignore").read())
    except json.JSONDecodeError:
        return

    rel = _rel(root, pkg_path)
    facts.languages.append(
        Fact(value="node", evidence=[Evidence(file=rel, line=1, snippet="found")])
    )
    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}

    for pkg, label in NODE_FRAMEWORK_PACKAGES.items():
        if pkg in deps:
            facts.frameworks.append(
                Fact(
                    value=label,
                    evidence=[
                        Evidence(file=rel, line=1, snippet=f'"{pkg}": "{deps[pkg]}"')
                    ],
                )
            )
    for pkg, label in NODE_DATASTORE_PACKAGES.items():
        if pkg in deps:
            facts.datastores.append(
                Fact(
                    value=label,
                    evidence=[
                        Evidence(file=rel, line=1, snippet=f'"{pkg}": "{deps[pkg]}"')
                    ],
                )
            )
    for pkg, label in NODE_STORAGE_PACKAGES.items():
        if pkg in deps:
            facts.storage.append(
                Fact(
                    value=label,
                    evidence=[
                        Evidence(file=rel, line=1, snippet=f'"{pkg}": "{deps[pkg]}"')
                    ],
                )
            )
    for pkg, label in NODE_QUEUE_PACKAGES.items():
        if pkg in deps:
            facts.queues.append(
                Fact(
                    value=label,
                    evidence=[Evidence(file=rel, line=1, snippet=f'"{pkg}"')],
                )
            )

    build_script = data.get("scripts", {}).get("build")
    if build_script:
        facts.build_commands.append(
            Fact(
                value=build_script,
                evidence=[
                    Evidence(file=rel, line=1, snippet=f'"build": "{build_script}"')
                ],
            )
        )
        if "vite" in deps:
            facts.static_output_dir = "dist"


def scan_repo(path: str, repo_url: str, head_sha: str) -> Facts:
    facts = Facts(repo_url=repo_url, head_sha=head_sha)
    facts.has_dockerfile = os.path.exists(os.path.join(path, "Dockerfile"))

    _scan_python(path, facts)
    _scan_node(path, facts)

    env_hits, port_hits = _scan_env_vars_and_ports(path)
    facts.env_vars = [
        Fact(value=name, evidence=evs[:5]) for name, evs in sorted(env_hits.items())
    ]
    facts.ports = [
        PortFact(port=port, evidence=evs[:5]) for port, evs in sorted(port_hits.items())
    ]

    return facts
