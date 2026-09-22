# F2-PR-002 — Fluent 2 Light Token & Shared-Style Foundation

**Status:** READY FOR DEV
**Depends on:** F2-PR-001
**Blocks:** F2-PR-003

## Objective
Introduce a semantic Fluent 2 light compatibility foundation without attempting feature-page migration in the same PR.

## File manifest
| Action | File |
|---|---|
| MODIFY | `frontend/src/index.css` |
| CREATE | `frontend/src/styles/fluent2-tokens.css` |
| CREATE | `frontend/src/styles/fluent2-primitives.css` |
| CREATE | `frontend/src/styles/__tests__/visualSystemRatchet.test.ts` |
| KEEP TEMP | Astryx CSS imports/package dependencies until F2-PR-003 replaces shell |

## Token mapping
Legacy product variables must stop being the target API. Provide semantic variables for canvas/surface/elevation, text primary/secondary/disabled, border subtle/strong, brand foreground/background, status success/warning/error/info, focus, hover/pressed/selected, typography, density, radius and shadow.

During transition, legacy variables may alias semantic tokens only as a compatibility bridge. Their values must be **light**, not dark/cyan. No feature should add a new reference to legacy aliases.

Examples of required direction:
- `--bg-primary` → compatibility alias to canvas;
- `--bg-secondary` → surface;
- `--text-primary/text-muted` → primary/secondary text;
- `--accent-cyan/accent-blue` → compatibility alias to brand semantic color, never neon cyan;
- `--glass-*` → remove product effect; no blur/glass visual;
- status variables → semantic status foreground/background/border pairs.

Use system/Segoe UI-compatible typography appropriate to Fluent 2. Do not introduce remote font loading.

## Shared primitive CSS
Define stable classes for button variants, fields/selects, message bars, status tags, toolbar/command bar, table shell, drawer/panel, skeleton/state surfaces and focus-visible behavior. This PR may add classes but must not broadly rewrite feature TSX.

## Ratchet test
Scan production `src/**/*.{css,tsx}` excluding tests/demo and an explicit temporary allowlist. Fail on newly introduced:
- Astryx imports outside allowlist;
- `#66fcf1`, `#45f3ff`;
- `backdrop-filter`/glass tokens;
- new declarations of `--accent-cyan`/legacy dark tokens outside compatibility file.
The allowlist must be enumerated and shrink in later PRs.

## Acceptance
Application remains functional while mixed migrated/unmigrated surfaces coexist. Default canvas/text are light-compatible. No feature semantics change. Full frontend tests/build green.
