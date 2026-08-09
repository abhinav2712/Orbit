"""Hand-rolled Gemini function-calling loop — no LangChain/CrewAI/agent frameworks.
Direct google-genai SDK only, per Orbit's judged differentiator requirement."""

from __future__ import annotations

import json
from typing import Callable

from google import genai
from google.genai import types

from engine.tools import TOOL, AgentContext, execute_tool

# ⚠️ Verify against Google AI Studio's current free-tier list — this space moves fast.
MODEL = "gemini-2.5-flash"
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
  emit_migration_checklist. Use read_file only when the Facts are genuinely ambiguous.
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
    client = genai.Client()  # reads GEMINI_API_KEY from env
    ctx = AgentContext(clone_path=clone_path)

    contents: list = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text=(
                        "Here are the verified Facts for this repository:\n\n"
                        f"{json.dumps(facts_json, indent=2)}\n\n"
                        "Propose a Zerops architecture, then emit a validated zerops.yaml, "
                        "then emit a migration checklist."
                    )
                )
            ],
        )
    ]
    config = types.GenerateContentConfig(
        system_instruction=ORBIT_ARCHITECT_PROMPT,
        tools=[TOOL],
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode="ANY")
        ),
        max_output_tokens=4096,
    )

    def emit(msg: str) -> None:
        if on_progress:
            on_progress(msg)

    for _ in range(MAX_TURNS):
        if ctx.repair_rounds_used > MAX_REPAIR_ROUNDS:
            emit("Gave up on yaml repair after 2 rounds; using last attempt.")
            break

        response = client.models.generate_content(
            model=MODEL, contents=contents, config=config
        )

        finish_reason = str(getattr(response.candidates[0], "finish_reason", "") or "")
        if finish_reason and "STOP" not in finish_reason:
            emit(f"Model stopped unexpectedly ({finish_reason}) — stopping.")
            break

        contents.append(response.candidates[0].content)

        calls = response.function_calls or []
        if not calls:
            break

        response_parts = []
        for call in calls:
            # ⚠️ UNVERIFIED: if this errors, run smoke_test.py and swap to call.function_call.name / .args
            emit(f"Running {call.name}...")
            result = execute_tool(call.name, dict(call.args), ctx)
            response_parts.append(
                types.Part.from_function_response(
                    name=call.name, response={"result": result}
                )
            )
        # ⚠️ UNVERIFIED: role="tool" per docs example — if rejected, try role="user"
        contents.append(types.Content(role="tool", parts=response_parts))

        if ctx.checklist is not None:
            emit("Migration checklist emitted — done.")
            break

    return ctx
