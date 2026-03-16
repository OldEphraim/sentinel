# Sentinel Decision Log

This file records non-trivial decisions made during development.
Append an entry at the end of every step.

---

## Step 1 — Monorepo scaffolding
**Decision:** Used pnpm workspaces monorepo with apps/ and packages/ separation.
**Alternatives considered:** Single flat repo; Turborepo; Nx.
**Reason:** pnpm workspaces is the lightest-weight option that still gives us workspace:* dependency linking between apps/web and packages/types. Turborepo/Nx add significant config overhead for a project of this size.
**Impact:** All Node packages are installed from the repo root with a single `pnpm install`. TypeScript path aliases between packages are handled by the workspace: protocol.
---

## Step 2 — Shared types package
**Decision:** Added `import type { AgentThought } from './agent'` explicitly in `order.ts`, despite the spec saying not to.
**Alternatives considered:** Following the spec verbatim (no import), relying on barrel-export resolution.
**Reason:** TypeScript does not resolve names across files via barrel exports — each file needs its own explicit imports. The spec's claim that `AgentThought` would be "resolved through the barrel export" is incorrect TypeScript behavior. Without the import, `tsc` emits `TS2304: Cannot find name 'AgentThought'`. The zero-errors success condition requires the fix.
**Impact:** `order.ts` has a direct import from `agent.ts`. This is standard TypeScript practice and has no negative downstream effects.
---
