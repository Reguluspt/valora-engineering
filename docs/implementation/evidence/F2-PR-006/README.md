# F2-PR-006 browser acceptance evidence

Captured with the Codex in-app Browser plugin `26.924.20706` at a 1280 × 720 viewport against the existing local browser fixture (`localhost:8000`) and Vite frontend (`localhost:5173`). The project is the disposable `project-acceptance` fixture. No production endpoint was used.

| Contract scenario | Browser result | Screenshot |
| --- | --- | --- |
| A. Normal populated surface | Six asset lines render in the dense table. | [Normal overview](00-normal-overview.jpg) |
| B. KPI summary | Total 6, selected 2, unselected 4, stale 1, eligible quotes 7; selected increments to 3 after confirmation. | [Normal overview](00-normal-overview.jpg), [confirmed overview](03-confirmed-overview.jpg) |
| C. Search/filter | Name search, no-results reset, and the `Cần xem lại` status filter work. | [No results](07-no-results.jpg), [stale decision](04-stale-decision.jpg) |
| D. Row → drawer | Table row opens a contextual, focusable drawer. | [Candidate drawer](01-candidates-warning.jpg) |
| E. Eligible candidates | Two server-projected candidates are selectable. | [Candidate drawer](01-candidates-warning.jpg) |
| F. Warning before confirmation | Candidate warnings appear before selection and beside the explicit confirmation, with price and source evidence. Warning does not block confirmation. | [Candidate warning](01-candidates-warning.jpg), [review before confirmation](02-review-warning-evidence.jpg) |
| G. Ineligible cannot commit | The server-projected no-eligible-candidate state has no selection control or confirmation button. A component test separately checks a disabled ineligible candidate. | [No candidate for one line](06-no-eligible-candidate.jpg), [no eligible candidates](13-ineligible-unavailable.jpg) |
| H. Current selection | The current supplier, quote price, difference, and evidence metadata appear in the decision tab. | [Stale current decision](04-stale-decision.jpg) |
| I. Stale selection | `Cần xem lại` appears without selecting a replacement automatically. | [Stale current decision](04-stale-decision.jpg) |
| J. History | Revision history remains visible in its own tab. | [History](05-selection-history.jpg) |
| K. Evidence/source context | Quote filename/status appears before confirmation; the current decision discloses filename, evidence ID, and status. | [Review before confirmation](02-review-warning-evidence.jpg), [stale decision](04-stale-decision.jpg) |
| L. Confirmation in progress | A second confirmation is disabled while the fixture response is pending. | [In progress](08-confirmation-processing.jpg) |
| M. Explicit confirmation success | The user chooses a candidate, reviews the warning and evidence, then confirms; the selected supplier and KPI update. | [Confirmed overview](03-confirmed-overview.jpg) |
| N. 409 conflict | The response clears the candidate choice, shows `Tải lại và xem lại`, and requires a fresh review/reconfirmation. | [Conflict](09-conflict-review.jpg) |
| O. Initial loading | A skeleton appears during the delayed aggregate response. | [Loading](11-loading.jpg) |
| P. Empty first use | Zero KPIs and a distinct first-use message appear. | [First use](10-first-use-empty.jpg) |
| Q. Empty no results | Search with no match shows a reset action; reset restores the table. | [No results](07-no-results.jpg) |
| R. Page/error recovery | A failed aggregate displays an error with `Thử lại`; retry after fixture recovery restores the page. | [Error/retry](12-error-retry.jpg), [normal overview](00-normal-overview.jpg) |
| S. Keyboard/focus | Enter and Space open a table row; the close control receives focus; forward Tab from outside the modal returns focus inside; Escape closes the drawer and returns focus to the originating row. | [Candidate drawer](01-candidates-warning.jpg) |

The production NCC selection aggregate projects only eligible candidates. The browser fixture follows that shape and uses an empty candidate list to represent unavailable candidates; the disabled-control case is covered by the focused component test. The fixture simulates server responses and revision changes but is not evidence of production persistence or tenant isolation. Those remain covered by the existing backend contract and CI.
