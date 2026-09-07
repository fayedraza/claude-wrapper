# Data factories

Deliberately empty. `data-factories.md`'s pattern (`createX(overrides)` + faker) needs a real production data shape to build from, and per `confidence-gate.md` a factory guessing at field validity rules is a fabrication, not a scaffold. This project has no domain models yet — Story 1.1 only ships a `/health` endpoint and the default Next.js page.

Add factories here once a story introduces real request/response shapes to model, and add `@faker-js/faker` to the root `package.json` devDependencies at that point (not installed yet — nothing uses it).
