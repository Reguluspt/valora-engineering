# VALORA UI/UX v2.3 — PR-02 Case Overview Frontend Contract

**Status:** MERGED FUNCTIONAL FOUNDATION — CURRENT FLUENT 2 LIGHT VISUAL CONFORMANCE REQUIRED
**Task:** `VALORA-PR02-IMPL-001` — Case State Frontend Hub Wiring
**Date:** 2026-09-05
**Prerequisite:** PR-01 read endpoint owner-closeout complete locally

**2026-09-21 visual-authority amendment:** PR-02 functional semantics and Case State wiring remain accepted. Historical browser checks do not establish current visual acceptance because the active frontend uses superseded dark/Astryx styling. `Tổng quan hồ sơ` must conform to the approved S10/Orchestration Hub Microsoft Fluent 2 light baseline; screenshot/visual-regression acceptance is required during OS-G0 remediation.

## 1. Scope

PR-02 renders the accepted `GET /api/v1/projects/{project_id}/case-state` projection as the
Vietnamese-first `Tổng quan hồ sơ` orchestration hub. It adds frontend API types, load/retry state,
route wiring and the approved Iteration 2 information hierarchy.

The task does not add or modify backend persistence, case-state derivation, resume context,
business commands, downstream stage providers, legacy approval/QC routes, commit, push or PR
publication.

## 2. Route Contract

- Case Overview: `#/workbench/projects/{project_ref}/overview`.
- Existing Workbench: `#/workbench/projects/{project_ref}`.
- The Workbench header exposes a contextual `Tổng quan hồ sơ` entry point.
- The App Shell Workbench item returns from Overview to the same project's existing Workbench.

Current accepted semantic route keys map to the existing project Workbench path:

```text
preliminary_request_pending
preliminary_analysis_pending
preliminary_ready_pending
official_intake_pending
```

The mapping chooses a destination only; it never marks a stage complete or derives workflow state.
Unknown/null keys, blockers without an authorized target route, unavailable stages and no-action
states must not produce a false navigation target.

## 3. Projection Presentation

The hub renders only server projection fields:

- current canonical stage with Vietnamese business label;
- all 16 ordered stage results and capability availability;
- one primary next-action panel;
- separate blocker, warning and stale counts/collections;
- bounded completion/capability counts derived from the returned stage list;
- `case_version` as secondary trace information.

Internal facts and fact tokens are never requested or reconstructed. Warning does not become
Blocking. `current_stage` and `next_action.stage` remain independent server values.

## 4. Cross-product States

- Initial load uses a layout-shaped skeleton.
- Load failure replaces the page with a Vietnamese page error and a real retry action.
- The frontend does not reconstruct state from legacy APIs when projection loading fails.
- Empty blocker/warning/stale areas use truthful `Chưa ghi nhận`/`Không có` copy.
- Unsupported next action is shown as unavailable; no disabled action masquerades as success.

## 5. Explicit Deferrals

- `PUT /api/v1/projects/{project_id}/resume-context` and durable resume state;
- recent-activity/audit aggregation not present in the projection;
- URLs for unimplemented downstream stage applications;
- frontend business-state inference or legacy workflow fallback;
- backend changes, migrations and new project mutations.

## 6. Acceptance Checklist

- [x] API client calls the exact case-state endpoint and propagates failures.
- [x] Project changes cannot show a stale prior projection.
- [x] Overview route and Workbench return route preserve project context.
- [x] All 16 stages render in server order with Vietnamese labels.
- [x] Blocker, warning, stale and unavailable/no-action semantics remain distinct.
- [x] Exactly one primary CTA renders only for an allowlisted semantic route key.
- [x] Loading, page-error and retry paths are covered.
- [x] No resume persistence, backend change or new legacy route.
- [x] Frontend tests, TypeScript lint and production build pass.

## 7. Verification Note

The in-app browser could not attach because its installed plugin and runtime service versions do
not match. Component rendering, route behavior, responsive CSS review and the production bundle
were verified; pixel-level browser inspection remains pending restoration of that external tool.
