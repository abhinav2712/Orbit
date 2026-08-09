<div align="center">

<img src="docs/logo.svg" width="120" height="120" alt="Orbit logo" />

# Orbit
### AI MIGRATION COPILOT FOR ZEROPS

**Point Orbit at any public GitHub repo. Get a launch-ready Zerops architecture in 60 seconds.**

A deterministic scanner reads your repo and cites its evidence. A hand-rolled agent reasons over that evidence — never inventing a service it can't point to. The output is a schema-validated `zerops.yaml`, an interactive architecture map, and a migration checklist, ready to commit.

![license](https://img.shields.io/badge/license-MIT-3cbdb2)
![python](https://img.shields.io/badge/python-3.12-3cbdb2)
![frontend](https://img.shields.io/badge/frontend-react%20%2B%20ts-3cbdb2)
![demo](https://img.shields.io/badge/demo-live-3ecf6e)
![llm](https://img.shields.io/badge/LLM-Gemini%202.5%20Flash-4d9fff)
![zerops](https://img.shields.io/badge/built%20on-Zerops-7c5cff)

**[Live demo →](https://web-2b46.prg1.zerops.app)**  ·  **[Source →](https://github.com/abhinav2712/Orbit)**  ·  **[Watch the 3-min demo →](ADD_VIDEO_URL_HERE)**

</div>

---

## What Orbit does

Migrating an app to Zerops means answering three questions nobody wants to answer by hand: which services does this app actually need, what does a correct `zerops.yaml` look like for them, and what has to change in the code to get there. Orbit answers all three automatically.

Paste a public GitHub repo URL. Orbit:

1. **Clones it into a sandbox** and runs a deterministic static scanner — no LLM involved — that extracts languages, frameworks, ports, datastores, queues, and environment variables, with a `file:line` citation for every single claim.
2. **Reasons over those facts** with a hand-rolled tool-use agent that proposes a Zerops service architecture, never inventing a service it can't point to evidence for.
3. **Emits and validates a** `zerops.yaml` against a schema/rule-checker, self-repairing up to twice if validation fails, and produces an ordered migration checklist with real doc links.

The result: an interactive architecture map, a downloadable `zerops.yaml`, a migration checklist, and the raw evidence report — all shareable via a permalink, all re-runnable.

---

## Why this isn't just an LLM wrapper

- **Deterministic core, AI on top.** The scanner (`engine/scanner.py`) never calls a model — it's pure static analysis. The agent only ever reasons over structured `Facts` with evidence, never raw repo bytes. This is what makes the output reproducible instead of a plausible-sounding guess.
- **Closed-loop validation.** Generated YAML is schema-checked before a human ever sees it (`engine/validator.py`). If it fails, the agent gets the exact errors back and gets two chances to fix them itself.
- **Hand-rolled agent loop, no framework.** `engine/agent.py` is a direct tool-use loop against the model API — no LangChain, no CrewAI, no agent framework. \~150 lines, and every line is explainable.
- **Sandboxed by design.** Shallow clone into an isolated temp directory, hard size/time caps, no code from the target repo is ever executed, path-validated file reads, `.git` stripped after use.
- **Self-referential proof.** Orbit can analyze its own repository — the architecture it proposes for itself is the same one it's actually running on.

---

## Architecture

Six Zerops services, one project, wired over the private network:

```
                         ┌──────────────── public traffic ────────────────┐
                         │                                                │
                   [ web ]  static React build              [ api ]  FastAPI
                         │   served by Zerops Static               port 8000, SSE + REST
                         └──────────────────┬─────────────────────────────┘
                                            │ private network
        ┌─────────────────┬────────────────┼───────────────┬────────────────┐
     [ db ]            [ cache ]       [ worker ]      [ storage ]
   PostgreSQL 16        Valkey        Python / RQ      Object storage
   analyses, results,   job queue,    clone → scan →   generated yaml,
   checklist state      SSE pub/sub,  reason → persist  scan reports,
                         result cache,                   checklist json
                         rate limits
```

| Service | Zerops type | Role |
| --- | --- | --- |
| `web` | Static (built with `nodejs@22`) | React + Vite SPA |
| `api` | `python@3.12` | FastAPI — REST + SSE, enqueues jobs, never clones a repo itself |
| `worker` | `python@3.12` | RQ consumer — clone → scan → reason → persist. Same codebase as `api`, different `zerops.yaml` block |
| `db` | PostgreSQL 16 (managed) | Analyses, checklist state |
| `cache` | Valkey (managed) | RQ queue, SSE pub/sub, result cache, per-IP rate limiting — one instance, four jobs, deliberately |
| `storage` | Object storage (managed, S3-compatible) | Generated `zerops.yaml`, raw scan reports, checklist JSON |

All service-to-service connections go through Zerops-injected environment variable references (`${postgresql_connectionString}`, `${valkey_connectionTlsString}`) declared in `zerops.yaml` — nothing is hardcoded. The model API key lives only on `worker`; `api` never holds it.

---

## The agent loop

```
messages = [system: ORBIT_ARCHITECT_PROMPT, user: Facts JSON + task]
while turn < MAX_TURNS:
    response = model.generate_content(tools=TOOLS, contents=messages)
    if response has a function call:
        run the tool, append the result, publish a progress event, continue
    else:
        break
```

Four tools, defined and executed in `engine/tools.py`:

| Tool | Purpose |
| --- | --- |
| `read_file` | Read a specific range of lines from the cloned repo — path-validated against the sandbox root, used only when the Facts are genuinely ambiguous |
| `propose_architecture` | Submit the service graph — one entry per proposed Zerops service, with reasoning and evidence references |
| `emit_zerops_yaml` | Submit a complete `zerops.yaml`; the executor runs it through the validator and returns either `{valid: true}` or the exact errors, giving the agent up to two repair attempts |
| `emit_migration_checklist` | Submit the ordered before/deploy/after checklist |

The system prompt carries a condensed Zerops service-type reference and two vendored few-shot examples — nothing fetched at request time. The model currently powering this is **Gemini 2.5 Flash** (see [Architecture decisions](#architecture-decisions-and-tradeoffs) below for why).

---

## Tech stack

| Layer | Choice |
| --- | --- |
| Frontend | React + TypeScript + Vite, Tailwind CSS v4, React Flow (`@xyflow/react`) for the architecture map |
| API | FastAPI, served on Zerops's Python runtime |
| Worker | RQ (Redis Queue) consumer on the same codebase as the API, different entrypoint |
| Database | PostgreSQL 16 (Zerops managed), SQLAlchemy 2.0 |
| Cache / queue / pub-sub | Valkey (Zerops managed) |
| Object storage | S3-compatible (Zerops managed) |
| LLM | Gemini 2.5 Flash via `google-genai`, direct SDK, hand-rolled loop |
| Live progress | Server-Sent Events, backed by Valkey pub/sub |

---

## Project structure

```
orbit/
├── zerops.yaml                  # pipeline config for api/worker/web
├── web/                         # Vite + React + TS frontend
│   └── src/
│       ├── pages/                (Home, Analysis, Gallery)
│       ├── components/           (RepoInput, ProgressStream, YamlViewer,
│       │                          ArchMap, ServiceInspector, Checklist, FactsReport)
│       └── lib/api.ts            # typed client + SSE helper
└── server/                      # shared Python package (api + worker)
    ├── app/
    │   ├── main.py                FastAPI app factory
    │   ├── routes/                 (analyses, events, health)
    │   ├── models.py               SQLAlchemy
    │   ├── schemas.py              Pydantic
    │   ├── queue.py                RQ setup + the analysis job
    │   └── deps.py                 db/cache/storage clients
    ├── engine/
    │   ├── cloner.py               sandboxed shallow clone
    │   ├── scanner.py              deterministic static analysis → Facts
    │   ├── agent.py                hand-rolled tool-use loop
    │   ├── tools.py                tool schemas + executors
    │   ├── validator.py            zerops.yaml schema/rule validation
    │   └── artifacts.py            object storage writes
    └── worker.py                  RQ worker entrypoint
```

---

## Known limitations & roadmap

Stated plainly, not hidden:

- **Scanner covers Python and Node today.** Go, Rust, Java, and PHP repos will return sparse evidence rather than a rich architecture — the agent correctly refuses to invent services it has no evidence for, so the honest failure mode is "too little", never "hallucinated too much."
- **Public GitHub repos only.** No private-repo OAuth, no GitLab/Bitbucket, no monorepo detection beyond simple manifest scanning.
- **No Alembic.** `Base.metadata.create_all()` on startup — the right call for a 48-hour build, a real tradeoff for anything longer-lived.
- **Doesn't execute the deployment.** Orbit hands you a validated `zerops.yaml` and a checklist; pushing it is still on you.

---

## Architecture decisions and tradeoffs

**Why Gemini, not Anthropic, for the runtime model.** The original design called for the Anthropic SDK directly. Mid-build, I switched the *implementation* to Google's Gemini API (`google-genai`) to use its free tier rather than a paid key. The architectural principle — a hand-rolled tool-use loop, no agent framework, deterministic Facts as the only grounding — is unchanged; only the SDK and model underneath it changed.

**Why** `requirements.txt` **sits at the repo root, not inside** `server/`**.** Zerops's `deployFiles`/`addToRunPrepare` path handling for nested-and-flattened folders isn't fully documented; keeping the dependency manifest at a location with zero path ambiguity removed a whole class of deploy bugs, at the cost of a slightly less "textbook" monorepo layout.

**Why the RQ worker needs its own Redis connection.** `deps.py` maintains two separate Redis clients — one with `decode_responses=True` for the app's own JSON/text data, one without, for RQ's queue. RQ pickles job payloads as raw bytes; sharing a decoding connection between the two caused a `UnicodeDecodeError` deep in the RESP3 parser the first time a real job ran.

---

## AI-use disclosure

This project was built for The Zerops Challenge using **Claude Code** (Anthropic) as an implementation partner throughout, and **Gemini 2.5 Flash** as the model powering Orbit's own analysis agent at runtime.

**Mine:** the product idea, the full PRD (problem framing, the Zerops service topology, the decision to hand-roll the agent loop instead of reaching for a framework, the API contract, the data model), every scope and architecture decision made under a 48-hour clock, and the sustained debugging across a live multi-service Zerops deployment — tracking down a mismatched env-var reference, an RQ/redis pickle-serialization conflict, a Valkey TLS requirement, a rate-limit-driven silent failure mode, and a CSS comment that accidentally closed itself early and broke a build, among others.

**Claude Code implemented, under my direction:** the large majority of the line-level code — the FastAPI/RQ backend (scanner, cloner, validator, the agent loop, the API routes) and the React/Tailwind frontend. I asked for full implementations rather than pseudocode for most of the build, reviewed what came back, and iterated through real deploy failures on Zerops until each piece actually worked — including catching and directing the fixes for every bug listed above.

I'm disclosing it this way rather than a more flattering version, because the rules I'm submitting under explicitly weigh honest disclosure, and because what's real here — the architecture, the decisions, standing up a working six-service system on a platform I hadn't used before this weekend — doesn't need the exaggeration.

## Credits:

Would like to thank <https://github.com/WeMakeDevs>

and  <https://github.com/zeropsio> for this opportunity and great hackathon!