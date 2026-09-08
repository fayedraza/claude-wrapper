import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/**
 * The isolated `.claude/` directory the E2E-run backend reads/writes,
 * via `CLAUDE_WRAPPER_CLAUDE_DIR` (see `backend/gateway/main.py`).
 *
 * Without this, a live (non-`TestClient`) backend process defaults to
 * this repo's own real `.claude/` directory -- confirmed by reproduction
 * during Epic 1 E2E setup: a manual UI check wrote a real permission
 * grant into the actual repo's `.claude/settings.local.json`, and
 * `.claude/settings.json` is git-tracked (not gitignored), so a
 * team-scoped grant or a Settings Router write would corrupt real repo
 * state on every E2E run. `playwright.config.ts`'s backend `webServer`
 * entry passes this path via `CLAUDE_WRAPPER_CLAUDE_DIR`;
 * `global-setup.ts` clears it once per full run so grants/rules from a
 * previous local run never leak into the next one (CI starts from a
 * fresh checkout either way, so this only matters for repeated local
 * `npm run test:e2e` invocations).
 *
 * The directory's basename must be exactly `.claude` -- also confirmed by
 * reproduction: `apply.py`'s `resolve_display_path()` (and `router.py`'s
 * display-path helpers) validate/render every `file_path` against
 * `claude_dir.name`, and every `file_path` this app ever sends or expects
 * is hardcoded to the literal `.claude/...` prefix. Pointing the override
 * at a directory named anything else (e.g. `.e2e-claude-dir`) makes every
 * `apply_action()` call fail with a 400 (`'.claude/rules/x.md' is not a
 * path under '.e2e-claude-dir/'`) -- isolation from the real directory and
 * matching its literal name are both required, not just one or the other.
 */
export const E2E_CLAUDE_DIR = path.join(__dirname, '../../_bmad-output/test-artifacts/e2e-workspace/.claude');
