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
