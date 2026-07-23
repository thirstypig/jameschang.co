---
id: DOC-001
type: intake-rules
project: portfolio
status: active
owner: james
tags: []
links: []
updated: 2026-07-23
---

# Feature intake rules — the gate before a PRD

Across the portfolio, a new feature idea does **not** get a PRD (and does not enter a
project's locked scope) until it can answer all five questions below. This is the
filter that keeps periphery from crowding out core.

1. **What problem, for whom?** — a real user and a real pain, not "it'd be cool."
2. **Which KPI does it move, and the target?** — name the metric and the number.
3. **Core or periphery?** — does it strengthen this project's core value, or is it a
   nice-to-have on the edge?
4. **What does it cost?** — build effort *and* ongoing run cost (infra, per-use, LLM).
5. **What are we deferring to fit it?** — nothing is free; name the trade.

**Rule:** nothing enters a project's `launch-spec` (locked scope) without a PRD that
clears this gate. The default answer to a new mid-cycle idea is **"not yet — log it in
the roadmap"**, not "let's build it."
