"""Hand-rolled Anthropic tool-use loop — no LangChain/CrewAI/agent frameworks.
Direct anthropic SDK only, per Orbit's judged differentiator requirement."""

from __future__ import annotations

import json
from typing import Callable

import anthropic

from engine.tools import TOOLS, AgentContext, execute_tool

MODEL = "claude-sonnet-5"
MAX_TURNS = 8
MAX_REPAIR_ROUNDS = 2

ORBIT_ARCHITECT_PROMPT = """You are a Zerops platform architect helping migrate a codebase onto Zerops.

You will receive a Facts object — deterministic static-analysis output with file:line evidence
for every claim (languages, frameworks, ports, datastores, queues, env vars). You did not gather
these facts yourself; trust them, and never invent a service, port, or dependency that isn't
backed by evidence in the Facts or by something you read yourself with read_file.

Rules:
- Prefer the smallest correct architecture. Don't propose a cache or worker service unless the
  Facts show a real need for one.
- Every zerops.yaml block you emit must trace back to a fact or a file you actually read.
- Use the tools roughly in this order: propose_architecture, then emit_zerops_yaml, then
  emit_migration_checklist. Use read_file only when the Facts are genuinely ambiguous about
  something load-bearing (e.g. which port an app actually binds).
- If emit_zerops_yaml returns validation errors, fix them and call it again. You get at most
  2 repair attempts — make them count.

Zerops service-type reference (condensed):
- Python apps            -> python@3.12   (or alpine/python@3.12)
- Node.js apps           -> nodejs@22     (or alpine/nodejs@22)
- Static SPA builds      -> static        (build with nodejs@22, run base: static)
- Go apps                -> go@1.22
- PostgreSQL             -> postgresql@16 (managed)
- Valkey (Redis-compat)  -> valkey@7.2    (managed)
- Object storage         -> object-storage (managed, S3-compatible)

zerops.yaml shape (one entry per service under a top-level `zerops:` list):
  zerops:
    - setup: <service-hostname>
      build:
        base: <base-image>
        buildCommands: [ ... ]
        deployFiles: [ ... ]
      run:
        base: <base-image>
        ports: [{ port: <int>, httpSupport: true }]
        envVariables: { ... }
        start: <command>

Few-shot 1 — a Python API with a Postgres dependency:
  zerops:
    - setup: api
      build:
        base: python@3.12
        buildCommands: [pip install -r requirements.txt]
        deployFiles: [.]
      run:
        base: python@3.12
        ports: [{ port: 8000, httpSupport: true }]
        envVariables: { DATABASE_URL: "${db_connectionString}" }
        start: uvicorn app.main:app --host 0.0.0.0 --port 8000

Few-shot 2 — a static React/Vite frontend:
  zerops:
    - setup: web
      build:
        base: nodejs@22
        buildCommands: [npm ci, npm run build]
        deployFiles: [dist/~]
      run:
        base: static
"""


def run_agent(
    facts_json: dict,
    clone_path: str,
    on_progress: Callable[[str], None] | None = None,
) -> AgentContext:
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    ctx = AgentContext(clone_path=clone_path)

    system = [
        {
            "type": "text",
            "text": ORBIT_ARCHITECT_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }
    ]
    messages = [
        {
            "role": "user",
            "content": (
                "Here are the verified Facts for this repository:\n\n"
                f"{json.dumps(facts_json, indent=2)}\n\n"
                "Propose a Zerops architecture, then emit a validated zerops.yaml, "
                "then emit a migration checklist."
            ),
        }
    ]

    def emit(msg: str) -> None:
        if on_progress:
            on_progress(msg)

    for _ in range(MAX_TURNS):
        if ctx.repair_rounds_used > MAX_REPAIR_ROUNDS:
            emit("Gave up on yaml repair after 2 rounds; using last attempt.")
            break

        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=system,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "refusal":
            emit("Model declined to continue — stopping.")
            break

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            break

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            emit(f"Running {block.name}...")
            result = execute_tool(block.name, block.input, ctx)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                    "is_error": bool(result.get("error")),
                }
            )
        messages.append({"role": "user", "content": tool_results})

    return ctx
