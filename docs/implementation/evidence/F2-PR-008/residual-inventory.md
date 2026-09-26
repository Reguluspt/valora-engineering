# F2-PR-008 residual inventory

Baseline: `4d32224ea31191e9f752ad5d848278da4f3e23d7` on `feat/operational-frontend-m365`.
This inventory was made before implementation edits. Counts below refer to tracked source and package declarations, not historical documentation.

| Family | Before | After | Class | Disposition |
| --- | ---: | ---: | --- | --- |
| Astryx direct packages | 3 | 0 | B: obsolete runtime/tool compatibility | Removed core, neutral theme and CLI. No source imported their JS. |
| Astryx package script | 1 | 0 | B | Removed. |
| Astryx CSS imports | 3 | 0 | B | Removed; canonical Fluent token and primitive imports remain. |
| Astryx probe component | 1 unmounted file | 0 | B | Removed per remediation contract; no importing consumer. |
| StyleX direct package | 1 | 0 | B | Removed; no source import or non-Astryx direct use. |
| Glass token declarations | 3 | 0 | B | Removed; zero consumers. |
| Legacy visual aliases | 10 declarations | 0 | B | Removed after retiring their only consumers in the isolated Review Queue demo. |
| Neon cyan literal | 1 in retired Review Queue component | 0 | B | Removed with the retired demo component. |
| Backdrop blur and legacy dark surfaces | 0 | 0 | A: active production | Zero occurrence ratchet retained. |
| Standalone Review Queue and Validation Dashboard routes | 0 registered routes | 0 | E: forbidden-route guards remain valid | Retained route prohibition constants; test explicitly asserts all four URLs absent from registry. |
| Obsolete dictionary keys | 15 (`nav.validate`, `nav.errorDashboard`, 13 `review.*`) | 0 | B | Removed after verifying no active consumers; removed obsolete i18n assertion. |
| Provider-specific parent workspace titles | 0 | 0 | A | Contextual OneDrive account/file terminology remains. |
| English user-facing common-state fallbacks | 2 (`Network connection error`, `Failed to load draft states`) | 0 | A | Translated active fallback messages. |
| Retired Review Queue demo source/tests | 10 files including `demo.html` | 0 | B | Removed disconnected demonstration surface; domain review state and current contextual validation remain. |
| Historical docs, tests describing prior debt, domain enum REVIEW | variable | retained | C/D/E | Preserved where they describe history, enforce guards, or express valid domain state. |

The app entry renders only the project list, case overview, Workbench, NCC Selection and Document Workspace. The retired Review Queue is reachable only from a separate `demo.html` entry, not production navigation. The `FORBIDDEN_NEW_STANDALONE_ROUTES` constant is a guard, not a route registry. No accepted compatibility contract requires the four legacy URLs.

Post-edit searches of `frontend/src` and `frontend/package.json` found zero production Astryx imports, theme-neutral, glass tokens, neon cyan literals, backdrop filters, or legacy visual aliases. The four legacy URL strings survive only as forbidden-route guard values. `npm audit --audit-level=high` reported zero vulnerabilities.
