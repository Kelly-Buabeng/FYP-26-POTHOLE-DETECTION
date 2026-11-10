# ADR 0001 — Modular monolith + separate ML inference worker

- **Status:** Proposed
- **Date:** 2026-11-10

## Context

v2 must serve citizens nationwide, with at least 200 concurrent users at launch and
headroom for 10× that. The team is small. Workloads split into two shapes:
I/O-bound request handling (reports, map queries, dashboards) and CPU/GPU-bound image
inference.

## Decision

- Build the core backend as **one deployable FastAPI application** split into
  internal modules (`auth`, `reports`, `incidents`, `media`, `geo`, `agencies`,
  `moderation`, `notifications`) with enforced boundaries: no cross-module table
  access; communication via service interfaces and domain events.
- Run **ML inference as a separate service** consuming jobs from a Redis-backed queue.
- Images are uploaded **directly to object storage** via presigned URLs, never through the API.

## Consequences

- Positive: one codebase/pipeline for the core; simple local dev; transactions stay
  in one database; ML scales and deploys independently; API stays responsive during
  upload bursts.
- Negative: core modules scale together. This is acceptable at the projected load
  (~40 req/s at 200 users, ~400 req/s at 2,000).
- Revisit if a single module needs very different scaling or its own team. Most
  likely candidates for extraction: `notifications`, `geo`/live updates.
