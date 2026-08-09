"""Sandboxed shallow-clone of a public GitHub repository."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass

import requests

GITHUB_URL_RE = re.compile(r"^https://github\.com/([\w.-]+)/([\w.-]+?)(\.git)?/?$")
MAX_REPO_SIZE_BYTES = 150 * 1024 * 1024
CLONE_TIMEOUT_SECONDS = 60


class ClonerError(Exception):
    """Base class for all cloner failures. Message is safe to show the user."""


class InvalidRepoURLError(ClonerError):
    pass


class RepoTooLargeError(ClonerError):
    pass


class RepoNotFoundOrPrivateError(ClonerError):
    pass


class CloneTimeoutError(ClonerError):
    pass


@dataclass
class ClonedRepo:
    path: str
    head_sha: str
    owner: str
    name: str


def parse_github_url(repo_url: str) -> tuple[str, str]:
    match = GITHUB_URL_RE.match(repo_url.strip())
    if not match:
        raise InvalidRepoURLError(
            "Only public GitHub repo URLs are supported, e.g. https://github.com/owner/repo"
        )
    return match.group(1), match.group(2)


def _github_headers() -> dict:
    token = os.environ.get("GITHUB_TOKEN")
    return {"Authorization": f"Bearer {token}"} if token else {}


def check_repo_size(owner: str, name: str) -> None:
    """Pre-clone size check via the GitHub API. Cheap — avoids wasting a clone on huge repos."""
    resp = requests.get(
        f"https://api.github.com/repos/{owner}/{name}",
        headers=_github_headers(),
        timeout=10,
    )
    if resp.status_code == 404:
        raise RepoNotFoundOrPrivateError(
            "Repo not found, or it's private. Orbit only supports public GitHub repos."
        )
    resp.raise_for_status()
    size_kb = resp.json().get("size", 0)
    if size_kb * 1024 > MAX_REPO_SIZE_BYTES:
        raise RepoTooLargeError(
            f"Repo is ~{size_kb // 1024}MB, over Orbit's 150MB cap."
        )


def _dir_size_bytes(path: str) -> int:
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            if not os.path.islink(fp):
                total += os.path.getsize(fp)
    return total


def clone_repo(repo_url: str) -> ClonedRepo:
    owner, name = parse_github_url(repo_url)
    check_repo_size(owner, name)

    dest = tempfile.mkdtemp(prefix="orbit-clone-")
    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", "--single-branch", repo_url, dest],
            capture_output=True,
            text=True,
            timeout=CLONE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        shutil.rmtree(dest, ignore_errors=True)
        raise CloneTimeoutError("Clone took too long (>60s) and was aborted.")

    if result.returncode != 0:
        shutil.rmtree(dest, ignore_errors=True)
        raise RepoNotFoundOrPrivateError(
            "Repo not found, or it's private. Orbit only supports public GitHub repos."
        )

    head_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=dest,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    # Strip .git now that we've extracted what we need from it — never gets scanned or shipped.
    shutil.rmtree(os.path.join(dest, ".git"), ignore_errors=True)

    if _dir_size_bytes(dest) > MAX_REPO_SIZE_BYTES:
        shutil.rmtree(dest, ignore_errors=True)
        raise RepoTooLargeError("Repo exceeds Orbit's 150MB cap for analysis.")

    return ClonedRepo(path=dest, head_sha=head_sha, owner=owner, name=name)


def cleanup(cloned: ClonedRepo) -> None:
    shutil.rmtree(cloned.path, ignore_errors=True)
