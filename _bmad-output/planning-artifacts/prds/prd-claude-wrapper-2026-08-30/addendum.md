# Addendum: Claude Wrapper PRD

Depth captured during discovery that belongs to a downstream document (architecture, solution design, UX spec) rather than the PRD itself.

## Context Matcher / Flight Path — mechanism detail (→ architecture / solution design)

User's own framing, useful for the architecture skill to expand on:

Each agent/subagent is assigned a graph built from its likely context sources: MCP servers, local filesystem docs, and existing Claude context. The Meta-Planner divides the combined context into subtopic nodes; LangGraph then instantiates and executes those nodes.

"Flight path" analogy (user's words): finding a path from a source node to a destination node is like flight routing —
- a path must exist from source to destination that covers all context the main/subagent needs (like a flight plan connecting origin and destination),
- "gas" (tokens) must not run out before the destination is reached (path must fit the token budget),
- "wind patterns" must stay in the same flow (the path should follow the direction of efficient token usage, not fight against it).

Net effect: the system searches for the node path that (a) covers the required context, (b) does not exceed the token budget, (c) is the most token-efficient route available, while still producing strong output quality. This is the mechanism behind the Execution Engine / flight path visualization already named in the architecture doc — worth expanding into a concrete routing/scoring algorithm at the architecture stage.

For an existing codebase, its own files are pulled into the same graph as subtopic nodes alongside MCP servers, local docs, and existing Claude context — the flight path can route through repo files directly.

## Control-tower agent sequencing (→ architecture)

User's framing: the main orchestrator agent acts like air traffic control ("control tower") for its subagents ("flights"). Subagents don't all start simultaneously — the control tower sequences takeoffs, starting one agent's task and holding dependent agents in a waiting state until it's safe (i.e. until the dependency is satisfied), then releasing the next. **This was first raised while discussing new-project behavior, but the user later confirmed explicitly (during PRD discovery) that it applies universally — existing repos and new repos alike (see PRD FR-11). It is not a new-project-only mechanism**, even though the source architecture doc's diagram/prose could otherwise be read as implying parallel-by-default execution. Worth formalizing at the architecture stage as an explicit dependency/ordering model in the DAG scheduler that applies to every run.

Terminology mapping surfaced during discovery, useful for the PRD Glossary: **flight** = a single agent/subagent's run; **control tower** = the main orchestrator agent; **flight path** = the actual execution route through context nodes; **cancelled flight** = a stopped/cancelled agent.

## Aesthetic and Tone (→ UX spec)

User explicitly wants a **colorful UI**, rejecting a dark-terminal aesthetic — a deliberate move away from the typical dev-tool/terminal visual language, even though the product itself is terminal-replacing. Worth carrying into the UX spec as a stated anti-reference ("not a dark terminal") plus a positive direction (color) to be refined with mockups/palette work.
