# Vietnamese i18n Label Dictionary Design Contract

This document outlines the localization and user shielding patterns for the Project Valora MVP client screens.

---

## 1. Purpose & Strategy
The Valora MVP is built to serve Vietnamese-first, non-IT end users. Displaying English labels, system status codes, or database column variables degrades trust and usability. 

This localization contract defines a type-safe key dictionary mapping all client text paths to user-friendly Vietnamese translations.

### 1.1 Relationship to Design Book v1.3
- Design Book v1.3 defines Vietnamese-first, non-IT UX, AI provider hiding, and MVP scope constraints.
- This dictionary implements the label foundation required by that design contract.

### 1.2 Relationship to Astryx Mapping
- Astryx controls visual patterns and component layouts.
- i18n controls user-facing text.
- Future Astryx component migrations must use this dictionary for all user-facing labels.

---

## 2. Forbidden Technical Terms Guardrail
Under no circumstances may any client view expose the following technical indicators to user interfaces:
- **Protocol Codes**: `401`, `403`, `409`, `422`, `500`
- **System Internals**: `API`, `RBAC`, `row_version`, `session_id`, stack traces
- **AI Backend Engines**: `Gemini`, `DeepSeek` (must always map to *Trợ lý Valora*)

---

## 3. Key Naming Strategy
Keys should be stable semantic identifiers, not raw Vietnamese phrases. Key names use English-like technical identifiers, but user-facing values must be Vietnamese and user-friendly.

Suggested grouping pattern:
- `action.*` (Common actions like save, cancel, refresh)
- `nav.*` (App shell/navigation labels)
- `project.*` (Project/Hồ sơ detail labels)
- `import.*` (Excel import pipeline actions/steps)
- `validation.*` (Data quality rules list)
- `workbench.*` (Live Workbench grid column labels)
- `context.*` (Asset Context drawer panels)
- `assistant.*` (Trợ lý Valora recommendation cards)
- `review.*` (QC reviews, return modal actions)
- `report.*` (Draft report selection checklists)
- `auth.*` (Login inputs, roles, expiration)
- `status.*` (Generic status tags)
- `empty.*` (Empty states descriptions)
- `confirm.*` (Confirmation messages)
- `error.*` (Friendly error messages)

---

## 4. Vietnamese-First UI Rules
- Vietnamese is the default UI language.
- Do not hardcode English user-facing labels in React components.
- Do not mix English and Vietnamese within the same visible user action flow.
- Business terms must be preferred over developer/technical terms.
- AI provider names must be hidden from ordinary users and replaced by “Trợ lý Valora”.

---

## 5. Adoption & Migration Plan
- **S10-PR-004**: Creates the dictionary foundation only — completed.
- **S10-PR-005**: Handles full non-IT error message registry — completed (see [VALORA_NON_IT_ERROR_MESSAGE_REGISTRY.md](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/docs/design/VALORA_NON_IT_ERROR_MESSAGE_REGISTRY.md)).
- **S10-PR-006 & S11+**: Apply labels progressively during Astryx / App Shell / Workbench migrations.

---

## 6. Review Blockers for Future PRs
To enforce compliance, the following items are flagged as automatic pull-request blockers:
- Any hardcoded English label in React components.
- Raw JSON logs or HTTP error codes displayed on UI cards.
- Directly exposing model names (e.g. "Gemini suggestion" instead of "Gợi ý từ Trợ lý Valora").
- Any new layout screen added that bypasses the localized `t()` function.
