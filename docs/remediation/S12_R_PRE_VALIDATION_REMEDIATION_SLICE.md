# S12-R — Pre-Validation Remediation Slice

**Tên đầy đủ:** Security, Workbench Routing & Excel Intake Hardening
**Mã slice:** `S12-R`
**Trạng thái:** `BLOCKING / REQUIRED`
**Base branch đề xuất:** `s12-pr-002-excel-file-upload-parser-intake`
**Blocked task:** `S12-PR-003 — Excel Staging Validation Engine`
**Ngày tạo:** 2026-07-11
**Design authority:** Valora Design Book v1.3, Astryx Design System, Valora engineering guardrails và các ADR hiện hành.

---

## 1. Lý do mở remediation slice

Audit chẩn đoán code tại đầu nhánh `s12-pr-002-excel-file-upload-parser-intake` phát hiện các lỗi có thể làm sai tenant boundary, bỏ qua Human Commit Gate, tạo dữ liệu nghiệp vụ giả trên Workbench và khiến Excel intake không an toàn trước file lớn.

Các lỗi này ảnh hưởng trực tiếp tới nền tảng mà `S12-PR-003` sẽ sử dụng. Vì vậy Validation Engine không được triển khai tiếp trên nhánh hiện tại trước khi remediation slice đạt PASS.

---

## 2. Mục tiêu

Slice này phải bảo đảm:

1. Danh tính người dùng không thể bị giả mạo bằng header do client tự khai báo.
2. Mọi Workbench session bị ràng buộc đúng user, organization và project.
3. Mọi thay đổi dữ liệu chính thức phải đi qua Human Commit Gate và audit transaction nguyên tử.
4. Toàn bộ Workbench sử dụng một project UUID đã resolve từ route, không có slug hoặc UUID hard-code.
5. Workbench không hiển thị dữ liệu taxonomy, currency, quote, unit hoặc identity giả.
6. Excel upload/parser có giới hạn tài nguyên thật, xử lý streaming và không làm mất staging cũ khi upload mới thất bại.
7. CI chạy được trên nhánh phát triển thực tế và cung cấp bằng chứng độc lập cho các audit report.
8. Tài liệu phase, handoff và audit phản ánh đúng trạng thái code.

---

## 3. Ngoài phạm vi

Slice này không triển khai:

- Staging Validation Engine.
- Apply/import staging rows vào `ProjectAssetLine`.
- AI-assisted column mapping.
- AI provider runtime.
- Báo cáo PDF/Word.
- Dashboard, CRM, doanh thu hoặc nghiệp vụ ngoài Valora MVP.
- Mở rộng field editable ngoài allowlist đã được phê duyệt.
- Thay đổi taxonomy hoặc valuation business rules không có trong Design Book/ADR.

---

## 4. Quy tắc blocking

Trong thời gian slice `S12-R` chưa PASS:

- Không merge `S12-PR-003`.
- Không thêm endpoint apply/import vào dữ liệu chính thức.
- Không đánh dấu Sprint 11 Live Workbench Loop là `READY`.
- Không dùng kết quả test ghi trong audit report thay cho CI run.
- Không thêm workaround bằng hard-code project, user, organization hoặc session ID.
- Không mở rộng phạm vi để “tiện refactor” các domain không liên quan.

---

# 5. PR breakdown

## S12-R-001 — Repository Baseline & CI Gate Repair

### Mục tiêu

Tạo baseline GitHub đáng tin cậy và bắt buộc quality gates trước khi sửa code nghiệp vụ.

### Phạm vi

- Thiết lập hoặc xác nhận nhánh `main` làm nhánh mặc định.
- Không dùng nhánh Sprint 0 làm default branch.
- Tạo branch protection cho `main`.
- CI chạy trên pull request và các branch thuộc `s12-*`.
- Thêm các job:
  - backend pytest;
  - PostgreSQL integration;
  - Alembic upgrade smoke;
  - frontend typecheck/lint;
  - frontend build;
  - frontend vitest;
  - secret scan;
  - dependency/security scan.
- Chạy `backend/tests/check_security.py` sau khi cập nhật danh sách rule để tránh false positive.
- Không dùng `npm install` khi lockfile tồn tại; ưu tiên `npm ci`.

### Acceptance criteria

- Một PR test cố ý làm backend test fail phải bị chặn.
- Một PR test cố ý làm frontend build fail phải bị chặn.
- Migration từ empty PostgreSQL database lên head thành công.
- Head commit có workflow run và required checks.
- Default branch không còn trỏ vào `s0-pr-001-root-rules-audit`.

### Tests/gates

```text
GitHub Actions required checks
PostgreSQL migration smoke
Backend pytest
Frontend lint/build/vitest
Secret/dependency scan
```

---

## S12-R-002 — Authentication Identity Boundary Hardening

### Mục tiêu

Loại bỏ khả năng giả mạo user bằng `X-User-Id`.

### Phạm vi

- Thực hiện theo ADR authentication/session hiện hành.
- Backend production không đọc danh tính từ `X-User-Id`.
- User ID và organization ID phải được suy ra từ access token/session đã xác thực.
- Access token ngắn hạn và refresh-token rotation phải được giữ đúng guardrail.
- Test có thể override dependency trực tiếp; không mô phỏng production auth bằng header tùy ý.
- Frontend API client gửi credential/token theo cơ chế được chọn.
- Chuẩn hóa lỗi `401/403` theo Non-IT Error Registry.

### Acceptance criteria

- Gửi `X-User-Id` thủ công không thể đăng nhập hoặc đổi danh tính.
- Token user A không thể trở thành user B.
- User inactive hoặc organization inactive bị deny-by-default.
- Frontend gọi API bảo vệ thành công bằng auth flow thật.
- Không log access token, refresh token hoặc secret.

### Tests/gates

```text
Token validation tests
Expired token tests
Refresh rotation/reuse tests
Inactive user/org tests
Identity spoofing regression tests
Frontend authenticated client tests
```

### ADR

Nếu ADR hiện hành chưa đủ chi tiết cho token transport, expiry, refresh storage hoặc revocation, phải cập nhật ADR trước khi viết code.

---

## S12-R-003 — Workbench Project & Session Tenant Scoping

### Mục tiêu

Mọi session và state của Workbench phải thuộc đúng user, organization và project.

### Phạm vi

- Tạo dependency/application service dùng chung để resolve session:
  - session ID đúng;
  - current user là owner hoặc có quyền được phê duyệt;
  - project thuộc organization hiện tại;
  - session đang active;
  - project ID khớp request context.
- Áp dụng dependency này cho:
  - create/get session;
  - heartbeat;
  - layout;
  - grid view;
  - selection;
  - panel state;
  - inline draft;
  - checkpoint;
  - undo/redo;
  - notification hoặc endpoint session-scoped khác.
- Trả `404` an toàn khi cross-tenant để tránh enumeration.
- Không tạo nhiều active session ngoài policy đã phê duyệt.
- Audit session start/end phải chứa organization, project và actor.

### Acceptance criteria

- User tenant A không thể tạo/read/heartbeat session thuộc tenant B.
- User A không thể điều khiển session riêng của user B.
- Session inactive/expired không thể ghi state.
- Session project A không thể mutate project B.
- Tất cả session endpoints dùng chung một scoping policy, không lặp logic tùy ý.

### Tests/gates

```text
Cross-tenant create/read/heartbeat tests
Cross-user ownership tests
Inactive session tests
Wrong-project tests
Permission revocation tests
```

---

## S12-R-004 — Official Mutation Command & Atomic Audit Gate

### Mục tiêu

Không còn đường ghi dữ liệu chính thức ngoài command/human-review/audit path.

### Phạm vi

- Tạo application command/service duy nhất cho commit draft.
- Transaction phải bao gồm:
  - validate permission;
  - validate workflow state;
  - exact optimistic version match;
  - validate typed field value;
  - mutate official row;
  - clear/close applied draft;
  - append AuditEvent;
  - commit một lần.
- Audit payload tối thiểu:
  - actor;
  - organization;
  - project;
  - session;
  - entity;
  - field;
  - before/after;
  - base/current version;
  - correlation ID;
  - command/event name.
- Direct endpoint `PATCH /asset-lines/{line_id}`:
  - loại bỏ field thuộc Workbench commit gate; hoặc
  - chuyển hoàn toàn sang cùng application command và yêu cầu explicit human confirmation.
- Không cho payload tự ghi `review_status` hoặc `validation_status` nếu không có command/workflow riêng.
- Không xóa ReviewDecision/AuditEvent; correction dùng reversal/change request.

### Acceptance criteria

- Không endpoint nào có thể đổi `appraised_unit_price` ngoài commit command đã audit.
- Nếu AuditEvent insert thất bại, official row không thay đổi.
- Version token phải bằng chính xác `row_version`; version tương lai cũng bị reject.
- `draft_value` sai kiểu không thể đi đến `setattr`.
- Commit không được kích hoạt AI, report hoặc background auto-approval.

### Tests/gates

```text
Atomic rollback test
Direct-mutation bypass test
Future-version rejection test
Typed value validation tests
Audit before/after payload tests
AI/report side-effect prohibition tests
```

---

## S12-R-005 — Dynamic Project Context & Live Workbench Data Integrity

### Mục tiêu

Loại bỏ hard-code project/session và dữ liệu nghiệp vụ giả khỏi frontend.

### Phạm vi

- Tạo `ResolvedProjectContext` hoặc kiến trúc tương đương:
  - route ref;
  - resolve UUID một lần;
  - cung cấp project UUID cho grid, session, context drawer, draft state và commit.
- Xóa:
  - `hd-98-gia-lai` hard-code trong component/hook;
  - all-zero project UUID;
  - hard-code organization/role/project title;
  - project route mặc định nghiệp vụ giả.
- WorkbenchLayout nhận project ref/UUID thật từ route.
- Adapter không được tự tạo:
  - fake canonical asset ID;
  - fake variant ID;
  - taxonomy path;
  - unit `cái`;
  - VND;
  - quote status;
  - quote value `0`.
- Missing data phải là `null`/empty state có nhãn tiếng Việt.
- Thêm pagination/infinite loading hoặc thông báo rõ số dòng chưa tải.
- Retry resolver phải thật sự chạy lại.
- Chuẩn hóa toàn bộ user-facing copy theo Vietnamese-first và Astryx.

### Acceptance criteria

- Mở project A và B tạo request đúng UUID tương ứng.
- Không request nào gửi slug hard-code hoặc zero UUID.
- Missing currency không hiển thị VND.
- Missing quote không hiển thị giá 0.
- Missing taxonomy hiển thị `Chưa phân loại`, không gán taxonomy giả.
- Grid có thể truy cập toàn bộ dataset qua pagination/loading.
- Không có English user-facing label trong luồng Workbench chính.

### Tests/gates

```text
Route-to-context tests
Two-project isolation UI tests
No-hardcode static scan
Null/missing-data rendering tests
Pagination tests
Vietnamese copy tests
```

---

## S12-R-006 — Excel Intake Streaming & Transaction Hardening

### Mục tiêu

Làm parser intake an toàn, hữu hạn tài nguyên và không phá staging cũ khi thất bại.

### Phạm vi

- Không dùng:
  - `file.file.read()` không giới hạn;
  - `list(ws.iter_rows(...))`.
- Thêm giới hạn:
  - request/file byte size;
  - compressed workbook size;
  - worksheet row count;
  - worksheet column count;
  - cell/string length hợp lý.
- Iteration streaming và dừng có kiểm soát.
- Nếu vượt giới hạn, reject toàn bộ upload; không silent truncation.
- Sheet được yêu cầu không tồn tại phải trả lỗi rõ ràng; không tự chuyển sheet âm thầm.
- Re-upload theo generation/transaction:
  - staging cũ giữ nguyên cho đến khi parse mới thành công;
  - parse lỗi không làm mất staging cũ;
  - batch status và audit được cập nhật nguyên tử.
- Raw cell preservation phải giữ column position/letter và duplicate header.
- Duplicate/blank header không được ghi đè dữ liệu.
- Formula, external links và macros không được thực thi.
- File extension check phải case-insensitive và thống nhất với registry.
- Parser exception ở mọi bước phải chuyển batch sang trạng thái phù hợp và tạo audit/event an toàn.

### Acceptance criteria

- File vượt giới hạn bị reject trước khi dùng bộ nhớ không kiểm soát.
- Workbook 5.001 dòng không bị cắt còn 5.000 dòng; toàn bộ batch bị reject với thông báo phù hợp.
- Upload mới thất bại không xóa staging đã có.
- Hai cột cùng header vẫn được lưu riêng.
- Sheet name sai không tự chuyển sheet.
- Không mutation `ProjectAssetLine`.
- Không công thức/macro/external link nào được thực thi.

### Tests/gates

```text
Large-file/large-row tests
Duplicate header tests
Blank header tests
Wrong sheet tests
Re-upload rollback tests
Formula/external-link safety tests
Official-data immutability tests
```

---

## S12-R-007 — Documentation Reconciliation & Final Acceptance

### Mục tiêu

Đồng bộ tài liệu với code và đóng remediation slice bằng bằng chứng có thể kiểm chứng.

### Phạm vi

- Cập nhật:
  - `README.md`;
  - `CODEX.md`;
  - `ENGINEERING_GUARDRAILS.md` nếu phase wording đã lỗi thời;
  - project handoff;
  - Sprint 11 final acceptance;
  - S12-PR-001/S12-PR-002 audit addendum.
- Không xóa lịch sử audit cũ; thêm addendum/reopen status.
- Đánh dấu Sprint 11:
  - `REOPENED / REMEDIATION REQUIRED` trong thời gian sửa;
  - chỉ trở lại `READY` sau final acceptance.
- Ghi rõ commit SHA, branch, CI run và test matrix.
- Audit phải phân biệt:
  - kiểm tra bằng code inspection;
  - kiểm tra bằng unit test;
  - kiểm tra bằng PostgreSQL integration;
  - kiểm tra bằng CI.
- Chạy final acceptance đầy đủ.

### Acceptance criteria

- Không tài liệu gốc nào còn nói dự án đang ở Sprint 0 như trạng thái hiện tại.
- Không audit nào khẳng định “no zero UUID fallback” nếu static scan vẫn tìm thấy.
- Không báo cáo PASS nếu required CI check chưa chạy.
- Mọi mâu thuẫn đã nêu trong remediation intake có disposition:
  - fixed;
  - accepted with ADR;
  - deferred có owner và target slice.

---

# 6. Thứ tự merge bắt buộc

```text
S12-R-001
   ↓
S12-R-002
   ↓
S12-R-003
   ↓
S12-R-004
   ↓
S12-R-005
   ↓
S12-R-006
   ↓
S12-R-007
   ↓
S12-PR-003 được phép bắt đầu/merge
```

Cho phép phát triển song song có kiểm soát:

- R-003 và R-005 có thể chuẩn bị song song sau khi contract của R-002 ổn định.
- R-004 và R-006 có thể phát triển song song nếu không sửa cùng vùng `projects.py`; ưu tiên tách router/service trước để giảm conflict.
- R-007 chỉ đóng sau khi tất cả PR trước đã merge và CI xanh.

---

# 7. Kiến trúc refactor tối thiểu đề xuất

Không yêu cầu broad refactor, nhưng nên tách các trách nhiệm mới để tránh tiếp tục phình `projects.py` và `models.py`.

```text
backend/app/modules/workflow_workbench/
  application/
    commit_asset_line_draft.py
    resolve_owned_session.py
  api/
    sessions.py
    drafts.py

backend/app/modules/project_master_data/
  api/
    projects.py
    asset_lines.py

backend/app/modules/excel_import/
  application/
    parse_workbook.py
    replace_staging_generation.py
  domain/
    limits.py
    column_mapping.py
  api/
    asset_imports.py

frontend/src/features/workbench/
  project-context/
  sessions/
  asset-grid/
  drafts/

frontend/src/features/asset-import/
  api/
  upload/
  staging/
```

Mọi thay đổi module boundary có tính lâu dài phải được ghi nhận bằng ADR hoặc cập nhật ADR kiến trúc hiện hành.

---

# 8. Definition of Done của toàn slice

Slice chỉ được đánh dấu PASS khi tất cả điều kiện sau đúng:

- [ ] Default branch và branch protection đúng.
- [ ] Required CI checks chạy trên head commit.
- [ ] Không còn production `X-User-Id` authentication.
- [ ] Không còn cross-tenant/cross-user Workbench session access.
- [ ] Không còn project slug hoặc zero UUID hard-code trong Workbench runtime.
- [ ] Không còn direct mutation bypass cho field official.
- [ ] Human commit và AuditEvent nằm trong cùng transaction.
- [ ] Exact optimistic version match được enforce.
- [ ] Workbench không hiển thị dữ liệu nghiệp vụ giả.
- [ ] Grid hỗ trợ toàn bộ dataset qua pagination/loading.
- [ ] Excel parser không đọc toàn bộ workbook vào list.
- [ ] Upload limits được enforce, không silent truncation.
- [ ] Re-upload failure không làm mất staging cũ.
- [ ] Duplicate header/raw cells được bảo toàn.
- [ ] PostgreSQL migration smoke PASS.
- [ ] Backend test PASS.
- [ ] Frontend lint/build/vitest PASS.
- [ ] Security/secret/dependency scan PASS.
- [ ] Tài liệu và audit addendum đã đồng bộ.
- [ ] Final acceptance report ghi commit SHA và CI evidence.
- [ ] Không có mutation `ProjectAssetLine` từ Excel intake.
- [ ] Không có AI auto-approval hoặc auto-commit.

---

# 9. Final acceptance matrix

| Khu vực | Gate bắt buộc | Trạng thái ban đầu |
|---|---|---|
| GitHub/default branch | Main/default + required checks | FAIL |
| Authentication | Không giả mạo identity từ client header | FAIL |
| Tenant boundary | Project/session/user scoped server-side | FAIL |
| Human commit | Command + exact version + atomic audit | FAIL |
| Direct update bypass | Không thể bypass gate | FAIL |
| Workbench routing | Dynamic resolved project context | FAIL |
| Workbench data integrity | Không fabricated business values | FAIL |
| Pagination | Có đường truy cập toàn bộ rows | FAIL |
| Excel memory safety | Streaming + limits | FAIL |
| Excel transaction safety | Failed re-upload giữ staging cũ | FAIL |
| Raw preservation | Duplicate headers không overwrite | FAIL |
| CI evidence | Workflow run trên head | FAIL |
| Documentation consistency | Phase/audit phản ánh code thật | FAIL |

---

# 10. Đầu ra bắt buộc của mỗi PR

Mỗi PR thuộc slice phải báo cáo:

```text
Task ID
Root cause
Files changed
Design/ADR sources
Security and tenant impact
Data mutation impact
Tests added
Commands run
CI run
Known limitations
Migration impact
Rollback plan
Runtime/user-visible behavior
Out-of-scope confirmation
Final PASS/FAIL
```

---

# 11. Quyết định sau remediation

Chỉ sau khi `S12-R-007` đạt PASS:

1. Cập nhật project handoff.
2. Chốt baseline commit mới.
3. Tạo nhánh mới cho `S12-PR-003`.
4. Triển khai Validation Engine chỉ trên staging rows.
5. Tiếp tục giữ nguyên nguyên tắc:
   - Excel là input, không phải source of truth;
   - staging trước, validation sau;
   - human review trước apply;
   - không mutation official data trong parser/validator;
   - AI chỉ đề xuất, không phê duyệt hoặc tự commit.

---

# 12. Current reconciliation (S12-R-007) — 2026-07-13

**Baseline `main` SHA:** `54872c764399182efae496e89dae9bd6ebdba9af`
**Active task:** S12-R-007 Documentation Reconciliation & Final Acceptance
**Overall slice disposition:** `BLOCKING` until R007 Draft PR CI + independent audit PASS
**Do not declare overall S12-R PASS from documentation-only state.** Independent re-audit still required after corrective documentation pass.

### ADR 0028 restricted-field scope note

Original slice wording that "every official change goes through Human Commit Gate" is **broader than runtime/ADR**.
Authoritative scope is ADR 0028: only `description`, `appraised_unit_price`, `review_status`, `validation_status`
are Workbench-gated via the draft-commit command. Non-restricted direct PATCH under `project:update` remains.
Excel intake still never mutates official `ProjectAssetLine`.

## 12.1 R001–R006 mapping (merged)

| Task | Merge subject / SHA on main | PR | Evidence types |
|---|---|---|---|
| S12-R-001 | `6c64305` Repository Baseline & CI Gate Repair | #1 | code, unit, CI gates, audit |
| S12-R-002 | `b025b97` Authentication Identity Boundary Hardening | #2 | code, unit, auth tests, audit |
| S12-R-003 | `c46ea1c` Workbench project and session tenant scoping | #3 | code, unit, tenant tests, audit |
| S12-R-004 | `e683757` Official mutation command atomic audit gate | #4 | code, unit, mutation/audit tests, audit |
| S12-R-005 | `ff40fda` Dynamic project context live data integrity | #5 | code, unit/frontend, audit |
| S12-R-006 | `54872c7` Excel Intake Streaming & Transaction Hardening | #6 | code, unit, PG CI (375/0 skip historical code-bearing), audit |

Historical R-006 code-bearing CI (branch head before squash, documented in R006 audit): backend **375 passed, 0 skipped, 27 warnings**, including:

```text
tests/test_s12_r_006_excel_intake_hardening.py::TestPGIsolatedConcurrencyRestored::test_concurrent_upload_serialization
```

## 12.2 Role of R007

- Reconcile README / CODEX / guardrails / handoff / historical audits with post-merge reality.
- Publish final acceptance matrix dispositions with evidence pointers.
- **Does not** implement Validation Engine or change runtime behavior.

## 12.3 Final acceptance matrix (slice-level)

| # | Area | Disposition | Source / PR | Evidence type | Limitation | Owner / target if deferred |
|---|---|---|---|---|---|---|
| 1 | default/CI baseline | FIXED | R-001 `6c64305` #1 | CI workflows + audit | Branch protection is repo-admin operational | — |
| 2 | authentication | FIXED | R-002 `b025b97` #2 | unit + auth tests + audit | Test overrides remain for fixtures | — |
| 3 | tenant isolation | FIXED | R-003 `c46ea1c` #3 | unit + API tests + audit | Enumerate-safe 404 patterns | — |
| 4 | official mutation command (ADR 0028 restricted fields only) | FIXED | R-004 `e683757` #4 + ADR 0028 | command path + forbidden PATCH tests | Non-restricted fields still use direct PATCH under project:update | — |
| 5 | human confirmation (restricted fields) | FIXED | R-004 + S11-PR-006 | API + frontend gate tests | Applies to description/appraised_unit_price/review_status/validation_status | — |
| 6 | version safety | FIXED | R-004 | optimistic lock tests | Required on restricted commit path; also used on direct PATCH | — |
| 7 | atomic audit (restricted commit path) | FIXED | R-004 | same-transaction audit tests | Non-restricted PATCH audit is not the R004 atomic-command model | — |
| 8 | dynamic project context | FIXED | R-005 `ff40fda` #5 | frontend resolve + tests | No fabricated slug fallbacks | — |
| 9 | fabricated-data removal | FIXED | R-005 | live data integrity tests | Panels still limited by backend domains | — |
| 10 | pagination/race safety | FIXED | R-005 + asset-lines API | pagination tests | Large datasets still need performance SLOs | DEFERRED product SLO owner |
| 11 | Vietnamese UX | FIXED | S10 + S11 | i18n/error registry tests | Ongoing label coverage | — |
| 12 | Astryx compliance | FIXED | S10 | design mapping + shell | Token drift needs design review | design owner ongoing |
| 13 | Excel bounded streaming | FIXED | R-006 `54872c7` #6 | parser + security scanner + tests | Local SQLite fixture recipe for savepoints | — |
| 14 | ZIP/XLSX security | FIXED | R-006 | zip safety tests + scanner | Threat model may expand | security review ongoing |
| 15 | resource limits | FIXED | R-006 | limit boundary tests | Limits versioned in domain policy | — |
| 16 | positional raw values | FIXED | R-006 + contract | raw persistence tests | Contract addendum must stay authoritative | — |
| 17 | failure preservation | FIXED | R-006 | transaction fault tests | PG multi-connection proof via CI | — |
| 18 | PostgreSQL concurrency | FIXED | R-006 CI | PG concurrency test PASS in CI | Local skip without PG still expected | — |
| 19 | ProjectAssetLine immutability (intake) | FIXED | R-006 | immutability snapshot tests | Apply path still deferred | S12 apply PR later |
| 20 | documentation consistency / R007 final acceptance | BLOCKED | R-007 | docs recon + Draft PR CI | Independent re-audit still required after corrective pass | R007 independent auditor |

Disposition key: only `FIXED`, `ACCEPTED WITH ADR`, `DEFERRED`, or `BLOCKED`. Totals for this 20-row matrix after corrective recon: **FIXED 19**, **ACCEPTED WITH ADR 0**, **BLOCKED 1** (row 20). Deferred product work (S12-PR-003, apply, AI, prod cert) is listed separately outside these 20 rows.

## 12.4 Remaining / deferred work

| Item | Disposition | Target |
|---|---|---|
| S12-R-007 Draft PR + CI + independent audit | BLOCKED (process) | R007 PR owner / auditor |
| S12-PR-003 Staging Validation Engine | DEFERRED / blocked on R007 | next engineering task |
| Apply staging → official lines | DEFERRED | post-validation PR |
| AI-assisted mapping | DEFERRED | later advisory-only PR |
| Production certification | DEFERRED | Sprint 8+ / ops |

## 12.5 Conditions to start S12-PR-003

1. S12-R-007 documentation head has green Draft PR CI.
2. Independent audit PASS for documentation reconciliation / slice closure.
3. This file and `docs/VALORA_PROJECT_HANDOFF.md` mark S12-PR-003 unblocked.
4. New branch from updated `main` — no reuse of R006/R007 branches for implementation.
