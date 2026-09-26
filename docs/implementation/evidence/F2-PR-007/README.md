# F2-PR-007 local acceptance evidence

Source: `frontend/scripts/browser-acceptance-server.mjs` and the Vite app at `http://localhost:5173`. The fixture supplies accepted connection, document, adoption, and Exchange artifact response fields. Its Working DOCX and Inbox XLSX are synthetic local records; it does not simulate a DocumentChangeCandidate or an official revision promotion.

## Browser states

| Acceptance | Evidence |
| --- | --- |
| A–E, S: provider-neutral workspace, project and selected document context, contextual OneDrive integration, truthful Working-copy authority boundary | [01-workspace-working.jpg](01-workspace-working.jpg) |
| G–H: explicit check and no-change presentation | [01-workspace-working.jpg](01-workspace-working.jpg); the browser check changed the fixture classification while VALORA revision remained 1 |
| I: outside-managed change | [03-revalidated-outside.jpg](03-revalidated-outside.jpg) |
| J: managed-region change remains unaccepted | [02-managed-change.jpg](02-managed-change.jpg) |
| K–L: replaced file and access unavailable recovery | [10-replaced-file.jpg](10-replaced-file.jpg), [11-access-unavailable.jpg](11-access-unavailable.jpg) |
| N: no documents / first use | [05-empty.jpg](05-empty.jpg) |
| O: page error and retry | [08-page-error.jpg](08-page-error.jpg); retry restored the normal workspace after fixture recovery |
| P: view-only user and distinct 403 denial | [06-permission-limited.jpg](06-permission-limited.jpg), [09-permission-denied.jpg](09-permission-denied.jpg) |
| Q–R: read-only provider and Exchange-ready provider | [07-read-only-provider.jpg](07-read-only-provider.jpg), [01-workspace-working.jpg](01-workspace-working.jpg) |
| T: visible keyboard focus | [12-keyboard-focus.jpg](12-keyboard-focus.jpg) |

The browser showed and invoked `Mở trong Word`. The local browser did not open a provider tab from the fixture's external URL, so that click establishes command availability only. The component test verifies the URL handoff and focus-return revalidation call. The browser also showed `Kiểm tra thay đổi` and, after invoking it, an outside-managed classification without a revision increment. The browser surface contains no `Nhập thay đổi` command for the Working DOCX, no review-labelled command wired to re-import, no `Khóa phiên bản`, no `Xuất PDF`, no fake Word editor, and no retired QC/reviewer workflow.

## Automated gates

- Focused M365 suite: 21 passing tests. It covers the DOCX re-import action's absence, XLSX Inbox re-import's preservation, five classifications, permission and capability gates, selected document context, non-authoritative check, focus return, and error states.
- Full frontend suite: 38 files and 217 tests passed. `npm run lint`, `npm run build`, `npm audit --audit-level=high`, and `git diff --check` passed.
- Exact-head backend/worker/frontend CI results belong to the eventual committed task head. The pre-task integration head was green; these fixture screenshots do not replace that final CI gate.

## Limits

The fixture proves presentation and local interaction against synthetic accepted response shapes. Component tests prove frontend branching and call boundaries with mocked API functions. Backend CI proves the committed backend and worker suites when run on the exact final head. Fixture evidence does not establish live Microsoft provider conformance, tenant isolation, or production persistence. No production Microsoft credentials were used.
