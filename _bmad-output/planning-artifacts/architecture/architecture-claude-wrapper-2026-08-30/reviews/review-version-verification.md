# Stack Table Version Verification

**Reviewed file:** `ARCHITECTURE-SPINE.md` — Stack table (lines 81-94)
**Review date:** 2026-08-30
**Method:** WebSearch against each claimed version/technology, independent of training-data assumptions.

---

## Next.js 16.3.x

**Verdict: confirmed-current.**

- Next.js 16.3 stable shipped 2026-08-03 (preview was June 2026). Headline features: "Instant Navigations" (SPA-like nav), lower dev-server memory (~90% reduction in long sessions), faster builds via cache reuse, `next build` on TypeScript 7, versioned docs for AI coding agents.
- Fit check: Next.js remains the default choice for a React app-router frontend with SSR/streaming needs; nothing has superseded it for this role.
- No deprecation/security advisory surfaced in this search that affects the 16.3.x line specifically.

Sources: [nextjs.org/blog/next-16-3](https://nextjs.org/blog/next-16-3), [releasebot.io Next.js updates](https://releasebot.io/updates/vercel/next-js)

---

## @xyflow/react (React Flow) 12.11.x

**Verdict: confirmed-current.**

- Latest published version found: 12.11.5 (published ~4 days before the search, i.e. late Aug 2026). Package is actively maintained, ~900+ dependent projects on npm.
- Fit check: React Flow / @xyflow/react is still the standard library for node-based/DAG canvas UIs in React — matches the spine's "DAG Canvas" use case well. No credible successor surfaced.
- No known deprecation. Note: the package was renamed from `reactflow` to `@xyflow/react` at the v12 boundary — the spine already uses the correct current package name, so this is fine, just worth knowing if anyone greps old docs referencing `reactflow`.

Sources: [npmjs.com/package/@xyflow/react](https://www.npmjs.com/package/@xyflow/react), [xyflow.com/blog/react-flow-12-release](https://xyflow.com/blog/react-flow-12-release)

---

## FastAPI 0.141.x

**Verdict: confirmed-current, but flag a dependency-pinning gap (see Redis/Starlette note below).**

- FastAPI 0.141.0 / 0.141.1 released 2026-07-29 and confirmed as the latest version on PyPI as of the search (Aug 2026). 0.141.1 was a same-day patch fixing background tasks/headers in `app.frontend()`.
- Fit check: FastAPI remains the standard for a Python async HTTP+WebSocket backend; still fully appropriate for the Gateway role described.
- **Flag — security:** CVE-2026-48710 ("BadHost"), a Host-header authentication-bypass vulnerability, affects **Starlette** (FastAPI's underlying ASGI toolkit) versions 0.8.3 through 1.0.0; fixed in Starlette 1.0.1+. Since FastAPI depends on Starlette via a version range rather than a strict pin (confirmed via a live `fastapi/fastapi` GitHub discussion titled "FastAPI dependency range still allows Starlette versions with published 2025 security advisories"), simply pinning `fastapi==0.141.x` does **not** guarantee a patched Starlette is installed. **Recommend the spine (or the build's dependency lock) explicitly pin `starlette>=1.0.1`** rather than relying on FastAPI's transitive resolution.
- Separately, CVE-2026-2978 (critical RCE, CVSS 9.8) affects FastAPI versions before 0.115.8 — not relevant to 0.141.x, noted only for completeness so it isn't mistaken for a current-version issue.

Sources: [github.com/fastapi/fastapi/releases/tag/0.141.0](https://github.com/fastapi/fastapi/releases/tag/0.141.0), [ionix.io/threat-center/cve-2026-48710](https://www.ionix.io/threat-center/cve-2026-48710/), [github.com/fastapi/fastapi/discussions/15193](https://github.com/fastapi/fastapi/discussions/15193)

---

## LangGraph (Python) 1.2.x

**Verdict: confirmed-current.**

- LangGraph 1.2 shipped 2026-05-11; latest patch found was 1.2.11 (2026-08-11). Reached 1.0 GA in Oct 2025, so 1.2.x by Aug 2026 is a plausible, unremarkable cadence.
- Key 1.2 features (per-node timeouts via `TimeoutPolicy`, node-level error handlers, `DeltaChannel`, v3 streaming API) are all consistent with the orchestrator-worker/checkpoint architecture the spine describes — nothing here contradicts the design.
- **Fit sanity-check:** LangGraph is still a leading choice for this role in 2026 — it overtook CrewAI in GitHub stars in early 2026 and has enterprise production users (Klarna, Uber, LinkedIn cited). Graph-based frameworks (LangGraph, Microsoft Agent Framework) remain the right category for "explicit orchestration of long-running, multi-actor workflows with durable checkpointing," which is exactly the spine's stated need (AD-1, AD-3, checkpointer requirement). Model-driven-loop frameworks (Strands, OpenAI Agents SDK) and role-based frameworks (CrewAI) are positioned as alternatives for different priorities (simplicity vs. control), not supersession — LangGraph has not been superseded for this use case.
- No deprecation/security advisory surfaced for the 1.2.x line.

Sources: [changelog.langchain.com](https://changelog.langchain.com/announcements/langgraph-1-0-is-now-generally-available), [langchain.com/resources/ai-agent-frameworks](https://www.langchain.com/resources/ai-agent-frameworks), [pypi.org/project/langgraph](https://pypi.org/project/langgraph/)

---

## FastMCP (Python) 3.4.x

**Verdict: confirmed-current.**

- Latest patch found: 3.4.7 (2026-08-10), consistent with 3.4.5 fixing an Ed25519/JWKS JWT-verification bug shortly before. Active, ongoing patch cadence through the review date.
- 3.4's headline feature (`fastmcp-remote`, a stdio-to-HTTP bridge) is directly relevant to the spine's "FastMCP bridge synthesis" (AD-6, dynamic_tools) role.
- **Fit sanity-check:** FastMCP remains the de-facto community standard for building MCP servers in Python — reportedly powers ~70% of MCP servers across all languages, and is recommended over the bundled low-level `mcp` SDK for anything beyond a fixed trivial tool server (composition/proxying/bridge-synthesis, which is exactly this project's use case). No successor or deprecation found.
- No deprecation/security advisory surfaced beyond the already-patched Ed25519/JWKS bug (fixed by 3.4.5, so 3.4.x as pinned is fine as long as it resolves to ≥3.4.5).

Sources: [gofastmcp.com/changelog](https://gofastmcp.com/changelog), [github.com/PrefectHQ/fastmcp/releases](https://github.com/PrefectHQ/fastmcp/releases)

---

## Pydantic 2.13.x

**Verdict: confirmed-current.**

- Pydantic 2.13.0 released 2026-04-13; latest patch found was 2.13.4 (2026-05-06), still the latest **stable** release as of the search (2.14.0 exists only as an alpha, 2.14.0a1, as of the search). So 2.13.x is not stale — it is the current stable line.
- Fit check: Pydantic v2 remains the standard for the project's stated role (SettingAction/SettingsRouterOutput schemas, Node model). No alternative surfaced or warranted.
- No deprecation/security advisory surfaced. Note the release included a `pydantic.v1` compatibility namespace update and a jiter bump fixing a musl-Linux segfault — informational only, not a concern for the pin itself.

Sources: [github.com/pydantic/pydantic/releases/tag/v2.13.0](https://github.com/pydantic/pydantic/releases/tag/v2.13.0), [pydantic.dev/articles/pydantic-v2-13-release](https://pydantic.dev/articles/pydantic-v2-13-release)

---

## redis-py 8.x (RESP3 by default)

**Verdict: confirmed-current, but flag a behavioral breaking-change already correctly noted by the spine's parenthetical.**

- redis-py 8.0 changed the default wire protocol from RESP2 to RESP3 (`DEFAULT_RESP_VERSION` 2→3), while keeping legacy RESP2-shaped Python return types by default for backward compatibility (`legacy_responses` flag controls this).
- **Flag:** this is a real breaking-change surface — connecting to a Redis server older than 6.0, or through a proxy that doesn't support the `HELLO` command, causes an **immediate connection failure** with no automatic RESP2 fallback in 8.0. Since the spine also pins **Redis 8.x** (not an older server), this is self-consistent and not a mismatch — but worth flagging explicitly in the spine or a build note so an implementer doesn't accidentally point redis-py 8.x at an older Redis instance, a Redis-proxy, or a Redis-compatible-but-not-identical service (e.g. some managed "Redis-compatible" caches) without testing the HELLO handshake.
- The spine's own annotation "(RESP3 by default)" already shows this was researched, not asserted — good.

Sources: [github.com/redis/redis-py/issues/4089](https://github.com/redis/redis-py/issues/4089), [redis.readthedocs.io/en/stable/resp3_features.html](https://redis.readthedocs.io/en/stable/resp3_features.html)

---

## Redis 8.x — "locally-run instance... not a hosted/managed service" claim

**Verdict: confirmed-current / reasonable claim, still holds.**

- Since Redis 8.0 (May 2025), Redis Ltd. moved to a **tri-license model**: RSALv2 (source-available, not OSI-approved) OR SSPLv1 (source-available, not OSI-approved) OR **AGPLv3** (OSI-approved open source) — the licensee's choice.
- Because AGPLv3 is an available option, **self-hosting Redis 8.x locally (including via Docker) remains fully free and unencumbered** for this project's use case — a locally-run developer tool. The official `redis` image is maintained on Docker Hub, and `docker run`/Docker Compose remains a normal, easy local path (Docker's own restart-policy handles reboots/restarts).
- The licensing complication that exists is specifically for **third parties who want to offer Redis-as-a-managed-service without being Redis Ltd.** (that's what drove the 2024 SSPL move and the subsequent AGPLv3 option) — it does not complicate local/self-hosted use at all. So the spine's framing (self-host locally, don't use a hosted/managed service) is not just reasonable but is *exactly* the framing that sidesteps any licensing friction — a well-chosen justification, not merely still-true by luck.
- No indication Redis 8.x has dropped Docker/local-install support or made it harder; if anything, AGPLv3 availability makes the local self-host story cleaner than the SSPL-only period (2024–2025) did.

Sources: [redis.io/blog/agplv3](https://redis.io/blog/agplv3/), [redis.io/legal/licenses](https://redis.io/legal/licenses/), [hub.docker.com/_/redis](https://hub.docker.com/_/redis), [upstash.com/blog/how-to-self-host-redis-in-2026](https://upstash.com/blog/how-to-self-host-redis-in-2026)

---

## Summary Table

| Technology | Version claimed | Verdict | Flag |
| --- | --- | --- | --- |
| Next.js | 16.3.x | confirmed-current | none |
| @xyflow/react (React Flow) | 12.11.x | confirmed-current | none |
| FastAPI | 0.141.x | confirmed-current | pin `starlette>=1.0.1` explicitly (CVE-2026-48710 BadHost; FastAPI's own dependency range doesn't guarantee this) |
| LangGraph (Python) | 1.2.x | confirmed-current | none; still the right category of tool for this role |
| FastMCP (Python) | 3.4.x | confirmed-current | ensure resolves to ≥3.4.5 (Ed25519/JWKS JWT bug fixed there) |
| Pydantic | 2.13.x | confirmed-current | none (2.14 still alpha-only as of review) |
| redis-py | 8.x | confirmed-current | note the RESP3-default breaking change / no-fallback-on-HELLO-failure behavior explicitly in build docs |
| Redis (server) | 8.x, local-only | confirmed-current | none — AGPLv3 option makes local/Docker self-host clean; claim holds |

**Overall:** all seven library/framework version claims and the Redis licensing/deployment claim check out as genuinely current and plausible for August 2026 — none read as stale or extrapolated from stale training data. Two items are worth folding into the spine or a build note (not version corrections, but operational hardening): (1) explicitly pin `starlette>=1.0.1` given FastAPI's loose transitive range and the BadHost CVE, and (2) call out redis-py 8.0's no-RESP2-fallback behavior so nobody points it at a non-HELLO-capable proxy/older server.
