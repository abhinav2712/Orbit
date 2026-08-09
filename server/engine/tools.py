"""Tool schemas + executors for the Orbit architect agent."""

from __future__ import annotations

import os
from dataclasses import dataclass

from engine.validator import validate_zerops_yaml

TOOLS = [
    {
        "name": "read_file",
        "description": (
            "Read a specific range of lines from a file in the cloned repository. "
            "Use this only when the provided Facts are genuinely ambiguous about something "
            "load-bearing — most of your reasoning should come from the Facts you were given."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path relative to the repo root, e.g. 'src/config.py'",
                },
                "start": {"type": "integer", "description": "1-indexed start line"},
                "end": {
                    "type": "integer",
                    "description": "1-indexed end line (inclusive)",
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "propose_architecture",
        "description": "Submit the proposed Zerops service graph once you've decided which services the repo needs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "services": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "zerops_type": {"type": "string"},
                            "role": {
                                "type": "string",
                                "enum": [
                                    "frontend",
                                    "api",
                                    "worker",
                                    "database",
                                    "cache",
                                    "storage",
                                ],
                            },
                            "reasoning": {"type": "string"},
                            "evidence_refs": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["name", "zerops_type", "role", "reasoning"],
                    },
                },
            },
            "required": ["services"],
        },
    },
    {
        "name": "emit_zerops_yaml",
        "description": (
            "Submit a complete zerops.yaml for validation. Returns {valid: true} on success, "
            "or the exact validation errors to fix — you get at most 2 repair attempts."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"yaml_text": {"type": "string"}},
            "required": ["yaml_text"],
        },
    },
    {
        "name": "emit_migration_checklist",
        "description": "Submit the ordered migration checklist for the developer to follow.",
        "input_schema": {
            "type": "object",
            "properties": {
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "phase": {
                                "type": "string",
                                "enum": ["before_deploy", "deploy", "after_deploy"],
                            },
                            "title": {"type": "string"},
                            "detail": {"type": "string"},
                            "docs_url": {"type": "string"},
                            "evidence_ref": {"type": "string"},
                        },
                        "required": ["phase", "title", "detail"],
                    },
                },
            },
            "required": ["steps"],
        },
    },
]


@dataclass
class AgentContext:
    """Mutable state the tool executors write into; agent.py reads it after the loop."""

    clone_path: str
    services: list | None = None
    zerops_yaml: str | None = None
    yaml_valid: bool = False
    checklist: list | None = None
    repair_rounds_used: int = 0


def _safe_join(root: str, rel_path: str) -> str:
    """Resolve rel_path under root, refusing to escape it (no .., no symlink breakout)."""
    root_real = os.path.realpath(root)
    target = os.path.realpath(os.path.join(root, rel_path))
    if target != root_real and not target.startswith(root_real + os.sep):
        raise ValueError("path escapes the repo sandbox")
    return target


def execute_tool(name: str, tool_input: dict, ctx: AgentContext) -> dict:
    if name == "read_file":
        return _read_file(tool_input, ctx)
    if name == "propose_architecture":
        ctx.services = tool_input["services"]
        return {"ok": True}
    if name == "emit_zerops_yaml":
        return _emit_zerops_yaml(tool_input, ctx)
    if name == "emit_migration_checklist":
        ctx.checklist = tool_input["steps"]
        return {"ok": True}
    raise ValueError(f"unknown tool: {name}")


def _read_file(tool_input: dict, ctx: AgentContext) -> dict:
    try:
        full_path = _safe_join(ctx.clone_path, tool_input["path"])
    except ValueError as e:
        return {"error": str(e)}
    if not os.path.isfile(full_path) or os.path.islink(full_path):
        return {"error": "file not found or is a symlink"}

    start = tool_input.get("start", 1)
    end = tool_input.get("end", start + 200)
    with open(full_path, "r", encoding="utf-8", errors="ignore") as fh:
        lines = fh.readlines()
    snippet = "".join(lines[max(start - 1, 0) : min(end, len(lines))])
    return {"content": snippet[:8000]}


def _emit_zerops_yaml(tool_input: dict, ctx: AgentContext) -> dict:
    yaml_text = tool_input["yaml_text"]
    errors = validate_zerops_yaml(yaml_text)
    if errors:
        ctx.repair_rounds_used += 1
        return {"valid": False, "errors": errors}
    ctx.zerops_yaml = yaml_text
    ctx.yaml_valid = True
    return {"valid": True}
