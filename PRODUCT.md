# DOMINO: product context

> Written from docs/PLAN.md §3, §11 and §16 without a live interview (the author was offline).
> Assumptions are marked (assumed). Correct them and the design follows.

## What it is
An autonomous supply-chain recovery agent on a FalkorDB graph. When a disruption hits (a flood, a fire), it traces the multi-tier impact, separates "exposed" from "projected late", tests recovery plans in graph sandboxes, asks a human to approve purchase commitments, executes, and verifies.

## Who uses the screen
- **Hackathon judges** watching a 3-minute video and clicking the live demo (primary, for now).
- **A supply-chain planner / incident lead** in an operations room (the story the demo tells).
- (assumed) Viewed on a 1440 px laptop or a projector, often on a dark screen-share; the video is recorded at 1440 px wide.

## The one surface
A single "war-room" screen in **Operate mode**: the user is in a task (understand the cascade, compare plans, approve, verify). Scanability and trust beat expression.

## Tone
Calm, exact, accountable. Every number on screen comes from an engine or the API. The words are the domain's own: exposed, projected late, protected (projected), fulfilled. "Not in the graph" never means safe.

## Visual brief (pinned by PLAN §11.3)
- Restrained dark slate, neutral grays, **one accent (blue)** for the agent and evidence.
- Semantic status colours only: red = disrupted, amber = exposed but covered, rose = projected late, green = protected.
- Inter for UI, JetBrains Mono for Cypher, ids and figures.
- No gradients, glow or neon. Motion only where it explains cause and effect (the hop-by-hop cascade).

## Anti-references
Generic SaaS dashboard cards with hero metrics; neon "cyber" control rooms; decorative charts that are not engine output.
