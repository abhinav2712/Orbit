# Orbit — AI Migration Copilot for Zerops
### Product Requirements Document v1.0
**Event:** The Zerops Challenge (WeMakeDevs × Zerops) · Aug 8–9, 2026 · Solo build by Abhinav
**Tagline:** *Point Orbit at any repo. Get a launch-ready Zerops architecture in 60 seconds.*

---

## 0. How to use this document (note to Claude Code / planning mode)

This PRD is the single source of truth for the build. Read it fully before writing code.

- Build in the phase order defined in **§10 Build Plan**. Do not skip ahead to polish before the core loop works end-to-end.
- The agent loop in **§6** must be **hand-written (~100–150 lines), no LangChain/LlamaIndex/CrewAI**. This is a deliberate, judged differentiator. Direct Anthropic SDK tool-use only.
- Every service must map to the Zerops topology in **§5**. If a design decision conflicts with that topology, the topology wins.
- All hackathon rule constraints in **§2** are hard requirements, not suggestions.
- Prefer boring, working code over clever code. The demo must survive judges clicking around unsupervised.

---

## 1. Problem & Vision

### 1.1 The problem
Developers who want to leave Heroku, Render, Railway, or a hand-rolled VPS face the same wall every time: they know their app, but they don't know the target platform's config format, service model, or deployment conventions. For Zerops specifically, the activation hurdle is writing a correct `zerops.yaml` and deciding how to decompose an app into Zerops services (runtimes, managed databases, caches, workers, object storage) on the private network.

This is a **cold-start problem for the platform itself**: Zerops is powerful precisely because it's multi-service, but that same richness makes the first deployment intimidating.

### 1.2 The vision
**Orbit is the on-ramp.** A developer pastes a public GitHub repo URL. An AI agent clones it, inspects it like a senior platform engineer would — package manifests, Dockerfiles, env usage, ports, DB drivers, queue clients, build scripts — and produces three artifacts:

1. A **validated `zerops.yaml`** ready to commit.
2. An **interactive architecture map** of the proposed Zerops services (frontend / API / DB / cache / workers / storage) with per-service reasoning.
3. A **migration checklist** — env vars to set, secrets to move, code changes needed (e.g., "replace local file writes with S3-compatible object storage calls"), and the exact Zerops docs page for each step.

Every analysis is saved, shareable via public link, and re-runnable.

### 1.3 Why this is unique (not another AI wrapper)
- **Sponsor-native:** Orbit isn't deployed *on* Zerops incidentally — Zerops is the subject matter. It generates Zerops configs, teaches Zerops architecture, and grows Zerops's funnel. It sits squarely in the organizers' own suggested "Zerops tools" category (yaml generator + migration assistant + architecture visualiser, unified).
- **Deterministic core, AI on top:** static analysis (manifest parsing, port detection, dependency fingerprinting) produces structured facts; the LLM reasons over facts, not raw guesses. This makes outputs reproducible and defensible to judges.
- **Self-referential proof:** Orbit's own repo is analyzable by Orbit. The demo closes with Orbit generating the `zerops.yaml` for itself — the config it's actually running on. No other submission will have that moment.
- **Hand-rolled agent loop:** direct Anthropic tool-use, no frameworks. Explainable line-by-line to judges (rule 14 defense).

---

## 2. Hackathon rule constraints (hard requirements)

| # | Rule | How Orbit satisfies it |
|---|------|------------------------|
| R2/R4 | Zerops meaningfully used in build/deploy/operation | Deployed on 6 Zerops services; product's entire purpose is Zerops onboarding |
| R3 | Live URL, reachable, stays up through judging | Public deployment, health endpoints, credit budget reserved (§11) |
| R5 | No Hello World; ≥3 services (frontend, backend, DB) | 6 services: static frontend, FastAPI API, Postgres, Valkey, Python worker, object storage |
| R7 | Head start allowed; project not finished before event | Planning/scaffolding pre-event only; feature code written Aug 8–9 |
| R9 | Submission: deployment + live URL + source + demo video + Zerops explanation | Checklist in §12 |
| R12/R13/R14 | AI use disclosed; meaningful original work; must explain architecture | AI tools disclosed in form; agent loop hand-written; this PRD *is* the architecture explanation |
| R15 | One project, not previously finished | New codebase, new repo |
| Social step | Public build post w/ name, explanation, video, live URL, Zerops usage, tags @WeMakeDevs @zeropsio | Content plan in §12 |

---

## 3. Target users & core use cases

**U1 — The migrator.** Has a working app on Render/Heroku/VPS. Wants: "what would this look like on Zerops, and what do I have to change?" → Runs analysis, gets yaml + checklist, follows it.

**U2 — The evaluator.** Considering Zerops, hasn't committed. Wants a zero-effort preview of the platform fit. → Pastes repo, sees the architecture map, understands Zerops's service model in 2 minutes without reading docs.

**U3 — The hackathon builder / ZCP user.** Building something new this weekend. Wants a correct starting `zerops.yaml` for their stack instead of trial-and-error. → Generates config, commits it, pushes.

**Out of scope for the 48h build (state explicitly in README as roadmap):** private repos (OAuth), monorepo multi-app detection beyond simple heuristics, actually executing the deployment on the user's behalf, non-GitHub sources.

---

## 4. Product spec — features & acceptance criteria

### F1. Repo analysis (core loop) — MUST HAVE
- Input: public GitHub repo URL (validate format; reject non-GitHub, private, >150MB repos with clear errors).
- On submit: create an analysis job, return `job_id` immediately (202), enqueue for the worker. **Never analyze synchronously in the API process.**
- Worker: shallow-clone (`--depth 1`), run the static scanner (§6.2), run the agent (§6.3), persist results, upload artifacts to object storage, publish progress events.
- Live progress in UI via SSE (Server-Sent Events) from the API, backed by Valkey pub/sub: `cloning → scanning → reasoning → generating → validating → done|failed`. Each stage streams a one-line human-readable status ("Detected FastAPI on port 8000", "Found psycopg2 → proposing PostgreSQL 16 service").
- **Acceptance:** pasting `https://github.com/tiangolo/full-stack-fastapi-template` (or similar known repo) yields a complete result in < 90s with no manual intervention.

### F2. `zerops.yaml` generation + validation — MUST HAVE
- Output a complete `zerops.yaml` covering every detected deployable service: `setup`, `build` (base, buildCommands, deployFiles), `run` (base, ports, envVariables placeholders, start), and managed services (Postgres, Valkey, object storage) where detected.
- **Validate before presenting:** schema-check the generated yaml against a vendored JSON Schema / rule set (ports are ints, base images are from a known-good allowlist, required keys present). If validation fails, the agent gets the errors back and retries (max 2 repair rounds) — mirrors ZCP's own "round again on failure" philosophy.
- UI: syntax-highlighted viewer, copy button, "Download zerops.yaml", and per-block inline annotations ("why this block exists").
- **Acceptance:** generated yaml passes the validator; annotations render; download works.

### F3. Architecture map — MUST HAVE
- Interactive diagram of proposed Zerops services: nodes (frontend/API/DB/cache/worker/storage), edges (who talks to whom over the private network), a "public traffic" boundary. Render with React Flow (preferred) or a clean SVG layout — no heavyweight diagram libs if React Flow suffices.
- Clicking a node shows: detected evidence ("found `redis==5.0` in requirements.txt", "PORT read in src/main.py:12"), the chosen Zerops service type/version, and reasoning.
- **Acceptance:** map renders for a 3+ service repo; node inspector shows real evidence strings from the scan, not generic text.

### F4. Migration checklist — MUST HAVE
- Ordered, actionable steps grouped as: *Before deploy* (env vars/secrets list extracted from code, code changes like filesystem→object storage), *Deploy* (push steps), *After deploy* (verify URLs, cron/queues). Each step links to the relevant Zerops docs URL.
- Checkboxes persisted per-analysis (local persistence in DB is fine; no auth needed — tie to analysis id).
- **Acceptance:** checklist reflects actual repo findings (e.g., lists the real env var names discovered).

### F5. Analysis history + shareable public links — MUST HAVE
- Every analysis has a permalink `/a/{slug}` viewable by anyone (this is what goes in the demo video and what judges click). Homepage shows recent public analyses as a gallery — social proof + instant demo content.
- **Acceptance:** permalink loads full results in a fresh incognito session.

### F6. "Analyze Orbit itself" easter egg — SHOULD HAVE (cheap, high demo value)
- A one-click button on the homepage: "🪞 Watch Orbit analyze Orbit." Pre-wired to Orbit's own repo. Results page gains a banner: "This is the architecture serving you this page right now."

### F7. Repeat-analysis cache — SHOULD HAVE
- Valkey cache keyed on `repo_url + head_commit_sha`, TTL 24h. Cache hit → instant results + "cached from Xh ago, re-run?" This is also the honest justification for Valkey existing in the architecture (judges will probe decorative services).

### F8. Rate limiting & abuse guards — MUST HAVE (operational)
- Per-IP rate limit (e.g., 5 analyses/hour) via Valkey. Repo size cap, clone timeout (60s), analysis wall-clock timeout (5 min), worker sandbox: clone into tmpfs, never execute repo code, never follow symlinks out of the clone dir, strip `.git` after scan.

---

## 5. Zerops deployment topology (the judged architecture)

Six services in one Zerops project, private-network wired:

```
                    ┌──────────── public traffic ────────────┐
                    │                                        │
              [ web ]  static React build          [ api ]  FastAPI, port 8000
                    │   (served by Zerops static)        │   SSE + REST
                    └──────────────┬─────────────────────┘
                                   │ private network
        ┌──────────────┬───────────┼──────────────┬──────────────┐
     [ db ]        [ cache ]   [ worker ]     [ storage ]
   PostgreSQL 16   Valkey      Python 3.12    S3-compatible
   analyses,       job queue,  clone+scan+    object storage:
   results,        SSE pub/sub,agent runner   generated yaml,
   checklist       result      (RQ consumer)  scan reports,
   state           cache                      diagram JSON
```

Service definitions (names are contract — use exactly these in code and yaml):

| Service | Zerops type | Purpose | Notes |
|---|---|---|---|
| `web` | static (or `nodejs@22` build → static deploy) | React SPA | Built with Vite; `deployFiles: dist` |
| `api` | `python@3.12` | FastAPI: REST + SSE, enqueues jobs | Never clones repos itself |
| `worker` | `python@3.12` | RQ worker: clone → scan → agent → persist | Same codebase as api (monorepo, two setups in one zerops.yaml) |
| `db` | PostgreSQL 16 (managed) | analyses, results, checklist state | Connection via Zerops-injected env vars |
| `cache` | Valkey (managed) | RQ queue backing store, SSE pub/sub, result cache, rate limits | One instance, four jobs — deliberate |
| `storage` | Object storage (managed) | yaml artifacts, raw scan JSON, diagram JSON | Public-read for artifact download links |

**Env/config principles:** all connections via env vars injected by Zerops service linking; `ANTHROPIC_API_KEY` as a Zerops secret on `worker` only (API service never holds it); one repo, one `zerops.yaml`, multiple `setup` blocks.

**Health:** `api` exposes `GET /healthz` (checks db + cache ping); `worker` heartbeats a Valkey key every 30s; `GET /healthz` reports worker liveness from that key. Judges hitting the URL must always get a healthy page.

---

## 6. System design

### 6.1 Monorepo layout
```
orbit/
├── zerops.yaml                  # all services, one file
├── web/                         # Vite + React + TS
│   ├── src/
│   │   ├── pages/ (Home, Analysis, Gallery)
│   │   ├── components/ (RepoInput, ProgressStream, YamlViewer,
│   │   │                ArchMap, Checklist, ServiceInspector)
│   │   └── lib/api.ts           # typed client, SSE helper
├── server/                      # shared Python package (api + worker)
│   ├── app/
│   │   ├── main.py              # FastAPI app factory
│   │   ├── routes/ (analyses.py, events.py, health.py)
│   │   ├── models.py            # SQLAlchemy
│   │   ├── schemas.py           # Pydantic request/response
│   │   ├── queue.py             # RQ setup
│   │   └── deps.py              # db/cache/storage clients
│   ├── engine/
│   │   ├── cloner.py            # shallow clone, sandbox, size caps
│   │   ├── scanner.py           # deterministic static analysis → Facts
│   │   ├── agent.py             # hand-rolled Anthropic tool-use loop
│   │   ├── tools.py             # tool defs + executors for the agent
│   │   ├── validator.py         # zerops.yaml schema/rule validation
│   │   └── artifacts.py         # object storage writes
│   └── worker.py                # RQ worker entrypoint
└── README.md                    # architecture writeup for judges
```

### 6.2 Deterministic scanner (`scanner.py`) — runs BEFORE the LLM
Produces a structured `Facts` object (Pydantic). No LLM involved. Detect:

- **Languages/runtimes:** presence+parse of `package.json` (engines, scripts, deps), `requirements.txt`/`pyproject.toml`, `go.mod`, `Cargo.toml`, `composer.json`, `Gemfile`.
- **Frameworks:** dependency fingerprints (fastapi/flask/django/express/next/nuxt/vite/react/rails/laravel/gin/chi...).
- **Ports:** regex scan for `PORT`, `listen(`, `uvicorn.run`, `app.run(port=`, EXPOSE in Dockerfile, vite/next config.
- **Datastores:** driver deps (psycopg/asyncpg/pg, pymongo/mongoose, redis/valkey/ioredis, mysql2, sqlite3) + connection-string env var patterns (`DATABASE_URL`, `REDIS_URL`, `MONGO_URI`).
- **Queues/workers:** celery, rq, bullmq, sidekiq deps; `Procfile` worker lines; cron patterns.
- **Storage:** boto3/aws-sdk/minio deps; local `open(.., 'w')` writes to non-tmp paths (flag for migration checklist).
- **Env vars:** all `os.environ`/`process.env` references, deduped, with file:line evidence.
- **Build signals:** Dockerfile stages, `npm build`/`vite build` scripts, static output dirs.

Every fact carries `evidence: [{file, line, snippet}]`. Evidence is what makes the node inspector (F3) feel real and what makes the agent grounded.

### 6.3 The agent (`agent.py`) — hand-rolled, ~100–150 lines
Direct `anthropic` SDK. Model: `claude-sonnet-4-6`. Loop shape:

```
messages = [system: ORBIT_ARCHITECT_PROMPT, user: Facts JSON + task]
while turn < MAX_TURNS(8):
    resp = client.messages.create(tools=TOOLS, messages=messages)
    if resp.stop_reason == "tool_use":
        run tool, append tool_result, publish progress event, continue
    else: break
```

**Tools (defined in `tools.py`):**
1. `read_file(path, start, end)` — read a specific file from the sandboxed clone (agent digs deeper only where Facts are ambiguous; path-validated against clone root).
2. `propose_architecture(services: [...])` — agent submits the service graph as structured JSON; executor persists draft, returns ok.
3. `emit_zerops_yaml(yaml_text)` — executor runs `validator.py`; returns `{valid: true}` or the exact validation errors, which the agent must fix (max 2 repair rounds).
4. `emit_migration_checklist(steps: [...])` — structured steps with `phase`, `title`, `detail`, `docs_url`, `evidence_ref`.

**System prompt principles:** "You are a Zerops platform architect. You receive verified Facts with evidence. Never invent a service without evidence. Prefer the smallest correct architecture. Every yaml block must trace to a fact." Include a condensed Zerops service-type/version reference and 2 few-shot yaml examples in the prompt (vendored, not fetched at runtime).

**Why this design wins judging:** deterministic facts → grounded reasoning → machine-validated output → self-repair loop. It's explainable end-to-end and mirrors ZCP's own verify-and-retry philosophy.

### 6.4 API contract (FastAPI)
```
POST /api/analyses            {repo_url}            → 202 {id, slug}
GET  /api/analyses/{id}                             → status + full result when done
GET  /api/analyses/{id}/events                      → SSE progress stream
GET  /api/analyses?public=1&limit=20                → gallery
POST /api/analyses/{id}/checklist/{step_id}/toggle  → checklist persistence
GET  /healthz
```
Result payload: `{status, facts_summary, services[], zerops_yaml, yaml_valid, checklist[], artifact_urls{yaml, report_json, diagram_json}, timings}`.

### 6.5 Data model (Postgres)
```
analyses(id uuid pk, slug text unique, repo_url text, head_sha text,
         status enum[queued,cloning,scanning,reasoning,generating,validating,done,failed],
         error text null, facts jsonb, services jsonb, zerops_yaml text,
         checklist jsonb, timings jsonb, created_at, completed_at)
checklist_state(analysis_id fk, step_id text, checked bool, pk(analysis_id, step_id))
```
Alembic optional — for 48h, `create_all` on startup is acceptable; note it as tradeoff in README.

### 6.6 Frontend spec (Vite + React + TS + Tailwind)
- **Home:** hero, repo input, "Analyze Orbit itself" button, gallery of recent analyses.
- **Analysis page (`/a/{slug}`):** progress stream while running (stage stepper + live log lines), then tabbed result: **Architecture** (React Flow map + inspector panel) / **zerops.yaml** (viewer + annotations + download) / **Checklist** / **Report** (facts + evidence).
- Design: dark, space/orbit motif, restrained — one accent color, real typographic hierarchy. It should look like a dev tool, not a template. (Consult frontend-design skill during implementation.)

---

## 7. What is genuinely hard here (judge-facing depth)

Call these out in README + demo — they're the "meaningful original work" evidence:
1. **Grounded generation:** the evidence-carrying Facts pipeline that keeps the LLM honest.
2. **Closed-loop validation:** generated yaml is schema-validated and machine-repaired before a human sees it.
3. **Async architecture done right:** queue-backed jobs, SSE progress, cache semantics, per-IP limits — the same production patterns from my day job, compressed into a weekend.
4. **Security posture for cloning arbitrary repos:** sandbox, no code execution, size/time caps, path validation on the agent's `read_file`.

---

## 8. Non-functional requirements
- p50 full analysis < 60s, p95 < 120s for repos ≤ 50MB.
- API stays responsive during analyses (worker isolation).
- Zero secrets in frontend or api service; key lives on worker only.
- Uptime through judging: health checks + conservative instance sizing + credit budget (§11).
- Graceful failure UX: a failed analysis shows *why* (clone timeout, unsupported stack) and never a blank page.

## 9. Success metrics (for the social post & README)
- Time-to-yaml for a real repo (target: "< 60 seconds" headline number).
- Number of distinct stacks handled in testing (target ≥ 6: FastAPI, Express, Next.js, Django, Go chi, static site).
- The self-analysis screenshot: Orbit's generated yaml vs. its actual running yaml, side by side.

---

## 10. Build plan (phased — this is the Claude Code execution order)

### Phase 0 — Pre-event (Wed–Thu, allowed head start: planning + platform setup only)
- Zerops account, ZCP quickstart, deploy a throwaway hello service to learn the platform. Delete it.
- Create empty repo, this PRD committed. No feature code.

### Phase 1 — Skeleton + deploy first (Sat morning, ~3h) — **deploy before features**
1. Monorepo scaffold per §6.1; FastAPI `/healthz`; Vite hello page; RQ worker that runs a no-op job.
2. Write `zerops.yaml` for all 6 services. Deploy. **Get the live URL green with all services connected before writing any product logic.** This de-risks the single most failable requirement (R3).

### Phase 2 — Core loop, ugly (Sat afternoon, ~5h)
3. `cloner.py` with sandbox + caps. 4. `scanner.py` for Python + Node ecosystems first. 5. `agent.py` + `tools.py` + `validator.py`. 6. Persist results; `POST /analyses` → worker → done; raw JSON visible at `/a/{slug}`.
**Milestone: end-to-end on the FastAPI template repo by Sat evening, however ugly.**

### Phase 3 — Result UI (Sat night → Sun morning, ~5h)
7. SSE progress stream + stage stepper. 8. yaml viewer + download + annotations. 9. React Flow architecture map + inspector. 10. Checklist with persistence. 11. Gallery + self-analysis button.

### Phase 4 — Hardening + breadth (Sun midday, ~3h)
12. Rate limits, cache (F7), timeouts, failure UX. 13. Add Go + static-site + Next.js scanner coverage. 14. Test against 6 public repos; fix top failures.

### Phase 5 — Ship package (Sun afternoon, ~3h)
15. README: architecture diagram, Zerops usage explanation, AI-use disclosure, tradeoffs, roadmap. 16. Demo video (≤3 min): problem → paste repo → live progress → map → yaml → self-analysis kicker. 17. Build post (X + LinkedIn; reel cut for TechShots) tagging @WeMakeDevs @zeropsio with name, explanation, video, live URL, Zerops usage. 18. Submission form incl. AI tools disclosure. 19. Incognito test of live URL + permalink.

---

## 11. Risks & mitigations
| Risk | Mitigation |
|---|---|
| Zerops learning curve burns Saturday | Phase 0 throwaway deploy; Phase 1 deploy-first rule |
| Agent yaml quality inconsistent | Deterministic Facts + validator repair loop + few-shot examples; cap MAX_TURNS |
| Credits exhausted before judging ends | Small instance sizes; kill throwaway project; monitor spend Sunday |
| Arbitrary repo edge cases crash worker | Timeouts, size caps, broad try/except → `failed` status with reason; never crash the worker process |
| Anthropic API latency/limits during demo | Cache (F7) pre-warms every repo shown in the video; demo uses cached runs live + one fresh run recorded |
| Scope creep on the map UI | React Flow defaults first; custom styling only in Phase 4 if time remains |

## 12. Submission checklist (final gate — do not submit until all ✓)
- [ ] Live URL up, healthy, incognito-tested
- [ ] Public repo with README architecture writeup
- [ ] Demo video recorded and linked
- [ ] `zerops.yaml` in repo == what's deployed
- [ ] Build post published, both handles tagged, all 6 required elements present
- [ ] Submission form filed with post link + AI disclosure (Claude Code, Claude — listed explicitly)
- [ ] Can explain, unaided: agent loop code, scanner design, every Zerops service's job, why Valkey/worker/storage exist
- [ ] Deployment left running through judging; credits checked
