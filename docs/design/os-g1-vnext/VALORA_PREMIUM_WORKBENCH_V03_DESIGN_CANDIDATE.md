# VALORA Premium Workbench v03 — Design candidate / 31-10-2026

**Status:** VISUAL DESIGN CANDIDATE — NOT APPROVED; no runtime authorization; this branch is a design-review checkpoint, not a new integrated implementation.

**Source baseline:** Draft PR #224 HEAD `fd65e94588579771380f5fe9b3a029931e39472c`, associated CI #687 (run ID `41219403573`) concluded SUCCESS prior to this design branch being created. Original Draft PR #223, #224 and Issue #222 baseline remain unmodified; UAT #203 remains separate/open.

## PO approval and scope

On 31 Oct 2026, PO approved creating a premium visual candidate to replace the overly plain appearance of UX-G1.15 v02, while retaining actual Microsoft Fluent UI React v9 as the eventual implemented component library and keeping business decisions already recorded in OS-G1 vNext. **This is approval to explore a design candidate, not final PO visual acceptance, merge, or production code rollout.**

## Delivered in current ChatGPT PM session

- Independently generated a **visual-review HTML** with working row selection, filter/search, table density, sidebar collapse, asset panel, price edit and summary simulation, plus desktop and summary screenshots. The HTML viewer uses standalone browser HTML/CSS/JS and **does not prove React rendering or Fluent compliance**.
- Generated **a separate Fluent React v9 source ZIP** based on the v02 prototype, carrying scoped MT01 and MT02A fixes. Retains business logic and four demonstration scenarios. Developer/local CI build and real browser verification are still outstanding. These files are ChatGPT session artifacts **not committed to this branch**.
- Local logic tests: **7/7 PASS**. TSX transpilation syntax diagnostics: **0**. Attempted offline `npm ci` but required cached dependency `yallist@3.1.1` unavailable. **No React npm build PASS claim**.
- Visual-preview browser smoke: no JavaScript page errors; table 6 rows; selecting next asset marks previous viewed; search filter and table density work; summary screen can be opened.

## Intended v03 visual changes

# VALORA Premium Workbench v03 — Fluent 2 React candidate

**Purpose:** An independently reviewable design candidate, **not approved product code**. Based on UX-G1.15 v02, carrying the scoped MT01/MT02A source fixes and preserving business interactions A-D, source evidence, human price overrides, and version simulation.

## Visual changes

- Premium, restrained light canvas, stronger title/KPI hierarchy, collapsible 66px icon-first sidebar.
- Table-first workbench: section header, visible asset count, grouped 13-column headers, three density presets, sticky STT and asset name, double synchronized horizontal scrollbars, natural mouse-wheel scroll chaining.
- Decision-first asset panel: proposed unit price in the first viewport, visible source/provenance/warnings, original price/editing controls remain below.
- Accessibility: Fluent TabList and Tab, explicit tab-to-panel relationships and focusable panels; keyboard row selection; reduced motion support.
- Existing mockup scenarios preserved: A auto-enrichment, B missing source/similar source, C identity proposal, D summary/version preview.

## Business boundaries

- Synthetic data only; edits are in-memory; no backend/API/schema/production/R2/UAT #203 changes.
- Staff controls proposed unit price; rematching does not silently overwrite manual edits. Viewed != formally accepted price basis. No per-line confirmation button.
- New version/export remains a simulation, NOT an Excel file.
- This is a candidate, not the PO-approved UX design; isolated from existing PR #224 and UX baseline.

## Run / verify

1. `npm ci`
2. `npm run test:logic`
3. `npm run build`
4. `npm run dev` and test A-D at desktop sizes and keyboard/zoom.

Prototype uses genuine `@fluentui/react-components` v9. No browser/runtime certification is claimed without an actual installed environment and SHA-pinned test evidence.

## Next independent checks / gates

1. **Design review:** PO reviews screenshot + interactive HTML before visually accepting v03. Existing mockup approved 26 Oct remains archive/baseline, not overwritten.
2. **Codex micro-task (not started):** restore dependencies in a clean worktree at pinned baseline, apply the downloadable v03 candidate ZIP as a scoped change in the prototype only, compare source and package-lock; no API, domain, schema, production frontend, CI/CD, UAT #203, or shared Knowledge Base changes.
3. `npm run test:logic`, `npm run build`, `git diff --check` and commit/SHA-pinned evidence.
4. Real browser cases A–D at 1440×900 and 1280×800, keyboard, tabpanel ARIA, zoom 125/200%, horizontal + mouse wheel scrolling, screenshots, console, browser errors.
5. Only after PO design and engineering Gate consider dedicated integration plan with domain/authority reconciliation; no merge/deploy implied.
