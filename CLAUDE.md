# CLAUDE.md — Sentinel

This file is the permanent context document for the Sentinel project. Read it fully at the start of every session. The step-by-step build plan lives in `STEPS.md` — read only the specific step you are currently executing from that file, not the whole thing.

---

## What we are building

Sentinel is a full-stack autonomous Earth intelligence monitoring agent built on SkyFi's geospatial platform API. Users define "watches" — an area of interest (drawn as a polygon on a map) plus a natural-language question — and an AI agent autonomously selects satellite data products, places orders via the SkyFi REST API, waits for async delivery via a RabbitMQ worker pipeline, interprets results using Claude tool-use, and delivers plain-English answers. The guiding thesis: imagery is a commodity; answers are the product.

---

## Monorepo structure

```
sentinel/
├── README.md
├── CLAUDE.md                   ← this file (always in context)
├── STEPS.md                    ← full step-by-step build plan (read per-step)
├── DECISION_LOG.md             ← append after every step
├── .env.example
├── .env                        ← never committed
├── .gitignore
├── docker-compose.yml
├── Makefile
├── pnpm-workspace.yaml
├── package.json                ← root, private: true
├── tsconfig.base.json
├── apps/
│   ├── web/                    ← Next.js 14 App Router (TypeScript, React, Tailwind, MapLibre GL)
│   ├── api/                    ← FastAPI (Python 3.11) — agent, SkyFi client, webhooks, SSE
│   └── worker/                 ← Python worker — RabbitMQ consumer, order polling, interpretation
├── packages/
│   └── types/                  ← shared TypeScript types
├── scripts/
│   └── seed.py                 ← demo data seeder
├── k8s/                        ← Kubernetes manifests
└── helm/sentinel/              ← Helm chart
```

---

## Conventions — read these carefully, they apply everywhere

**Package managers**
- Node.js: `pnpm` (monorepo with `pnpm-workspace.yaml`). Never use `npm` or `yarn`.
- Python: `uv`. Never use `pip` directly or `poetry`.

**Language versions**
- Python: 3.11 exactly (set in `.python-version` files)
- Node: 20+
- TypeScript: strict mode, `noUncheckedIndexedAccess: true`, `exactOptionalPropertyTypes: true`

**Python conventions**
- All functions that touch I/O must be `async`/`await`. No sync blocking in async contexts.
- Full type hints on every function signature and class attribute.
- snake_case for everything.
- Pydantic v2 for all schemas. SQLAlchemy 2.0 async ORM for all database access.

**TypeScript conventions**
- No `any` types except where explicitly noted in STEPS.md.
- PascalCase for components and interfaces. camelCase for variables and functions.
- All API calls go through `apps/web/src/lib/api.ts` — never fetch directly from components.

**Environment variables**
- Every service reads config from environment variables via its settings module. Never hardcode connection strings, API keys, or ports.
- `.env` is gitignored. `.env.example` is committed with keys but no values.

**Error handling**
- All FastAPI route handlers must have try/except covering external calls (database, RabbitMQ, SkyFi API). Return structured JSON errors, never let exceptions propagate as 500s with stack traces.
- The worker must never crash on a single bad message. Catch exceptions per-message and log them.

**File paths**
- All paths in STEPS.md are relative to the repo root (`sentinel/`) unless otherwise stated.

---

## Environment variables reference

```
# SkyFi Platform API
SKYFI_API_KEY=                  # From SkyFi Pro account settings. Leave empty to use mock.
SKYFI_API_BASE_URL=https://app.skyfi.com/platform-api
SKYFI_WEBHOOK_SECRET=           # For validating incoming SkyFi webhooks

# Anthropic
ANTHROPIC_API_KEY=              # From console.anthropic.com — required even for mock mode

# Postgres (PostGIS)
DATABASE_URL=postgresql://sentinel:sentinel@localhost:5432/sentinel

# RabbitMQ
RABBITMQ_URL=amqp://guest:guest@localhost:5672/

# App
NEXT_PUBLIC_API_URL=http://localhost:8000
SECRET_KEY=                     # 32-char random hex: openssl rand -hex 32
```

When `SKYFI_API_KEY` is empty, all SkyFi client methods automatically fall back to the mock implementation in `apps/api/src/services/mock_skyfi.py`. The mock simulates realistic delivery delays and returns plausible analytics data.

---

## Decision log

`DECISION_LOG.md` lives at the repo root. **Append to it at the end of every step.**

A non-trivial decision is any choice where:
- You picked one approach over a reasonable alternative
- You deviated from STEPS.md (even slightly) due to a constraint
- You chose a specific library version, config value, or default another engineer might have chosen differently
- You worked around an error or incompatibility in a non-obvious way

**Entry format:**
```
## Step N — <step title>
**Decision:** <what you decided>
**Alternatives considered:** <what else was possible>
**Reason:** <why>
**Impact:** <what this affects downstream, if anything>
---
```

If a step involved no non-trivial decisions, write:
`## Step N — <step title>: no non-trivial decisions.`

---

## How to work through the steps

At the start of each step:
1. This file (`CLAUDE.md`) is already in your context.
2. Read **only the current step** from `STEPS.md`.
3. Execute the step completely, verifying the described behavior at the end.
4. Append to `DECISION_LOG.md`.
5. Stop and wait for human review before reading the next step.

Do not read ahead in `STEPS.md`. Do not combine steps. Do not proceed past a step until its verification criterion is met.

---

## Notes for Claude Code

- Prefer explicit, readable code over clever code. This is a portfolio project read by humans.
- When you encounter an import error or missing dependency, fix it immediately — don't work around it.
- If something in STEPS.md conflicts with a convention in this file, follow this file and log the conflict in DECISION_LOG.md.
- The mock SkyFi client is the most important thing for making the demo work without real API credentials. Its data must be realistic enough that the agent's reasoning looks coherent.
- If you need to make a decision not covered by the spec, make the simpler choice, add a `# TODO:` comment, and log it.