

## S12-R — Pre-Validation Remediation Slice



Bạn đang làm việc trong repository:



```text

https://github.com/Reguluspt/valora-engineering

```



## 1. Vai trò



Bạn đóng vai trò:



```text

Senior Software Architect

Senior Application Security Engineer

Backend/Frontend Implementation Engineer

Database and Migration Engineer

Independent Quality Gate Executor

```



Nhiệm vụ của bạn là sửa các lỗi được phát hiện trong cuộc audit toàn repository Valora.



Bạn không chỉ viết code để test pass. Bạn phải bảo đảm:



```text

security boundary đúng

tenant isolation đúng

official data mutation đúng

audit trail đúng

Workbench dùng dữ liệu thật

Excel intake an toàn

CI tạo được bằng chứng độc lập

tài liệu phản ánh đúng code

```



---



## 2. Trạng thái repository hiện tại



Nhánh chứa baseline mới nhất:



```text

s12-pr-002-excel-file-upload-parser-intake

```



Commit baseline đã audit:



```text

b7042e78fda96cc8ad3e5292ce02611800e7c64b

S12-PR-002 Excel file upload parser intake

```



Không được triển khai tiếp:



```text

S12-PR-003 — Excel Staging Validation Engine

```



cho đến khi remediation slice này đạt PASS.



---



## 3. Tài liệu bắt buộc phải đọc trước khi sửa code



Trước khi thay đổi bất kỳ file nào, hãy đọc và tóm tắt:



```text

README.md

CODEX.md

ENGINEERING_GUARDRAILS.md

PR_RULES.md



docs/design/VALORA_DESIGN_BOOK_V1_3_MVP_COMPLETION_ADDENDUM.md

docs/design/VALORA_ASTRYX_TOKEN_COMPONENT_MAPPING.md

docs/design/VALORA_VIETNAMESE_I18N_LABEL_DICTIONARY.md

docs/design/VALORA_NON_IT_ERROR_MESSAGE_REGISTRY.md

docs/design/VALORA_LIVE_WORKBENCH_ASSET_LINES_API_CONTRACT.md

docs/design/VALORA_EXCEL_IMPORT_STAGING_CONTRACT.md



docs/audits/S11_PR_007_SPRINT_11_FINAL_ACCEPTANCE_AUDIT.md

docs/audits/S12_PR_001_EXCEL_IMPORT_CONTRACT_STAGING_MODEL_AUDIT.md

docs/audits/S12_PR_002_EXCEL_FILE_UPLOAD_PARSER_INTAKE_AUDIT.md



docs/adr/

```



Nếu repository có file:



```text

docs/remediation/S12_R_PRE_VALIDATION_REMEDIATION_SLICE.md

```



thì đây là remediation contract chính và bắt buộc phải đọc đầy đủ.



Nếu file chưa tồn tại, hãy tạo file đó từ remediation scope trong prompt này trước khi bắt đầu implementation.



Không được dựa riêng vào các audit report cũ vì audit đã phát hiện một số kết luận `PASS/READY` không khớp code runtime.



---



## 4. Các lỗi audit bắt buộc phải xử lý



### 4.1 Authentication có thể bị giả mạo



Production backend đang sử dụng:



```text

X-User-Id

```



do client tự gửi để xác định user.



Điều này cho phép người gọi giả mạo UUID của user khác.



Yêu cầu:



```text

Không dùng X-User-Id làm production authentication.

User và organization phải được suy ra từ credential đã xác thực.

Test được phép override dependency, nhưng không được mở backdoor production.

Không log token hoặc credential.

```



---



### 4.2 Workbench session thiếu tenant và ownership boundary



Các endpoint session có thể chỉ tìm bằng project ID hoặc session ID mà không xác nhận đầy đủ:



```text

organization

current user

project

session ownership

active status

```



Yêu cầu:



```text

Mọi session endpoint phải enforce server-side:

current user

current organization

allowed project

session ownership

active session status



Cross-tenant phải trả safe 404.

Frontend visibility không được coi là security.

```



---



### 4.3 Human Commit Gate có thể bị bypass



Hiện có direct mutation endpoint có khả năng thay đổi dữ liệu chính thức mà không đi qua draft/human confirmation.



Commit draft cũng chưa bảo đảm AuditEvent nằm cùng transaction với mutation.



Yêu cầu:



```text

Không official mutation ngoài application command đã phê duyệt.

Mutation, draft clearing và AuditEvent phải atomic.

Nếu audit insert thất bại, official mutation phải rollback.

Không cho client tự sửa review_status hoặc validation_status qua generic update.

```



---



### 4.4 Workbench có hard-code project



Frontend hiện có dấu hiệu hard-code:



```text

hd-98-gia-lai

00000000-0000-0000-0000-000000000000

```



Yêu cầu:



```text

Route project reference phải được resolve một lần.

Resolved project UUID phải được truyền cho:

asset grid

session

draft state

draft synchronization

context drawer

commit

pagination



Không component/hook nào được hard-code project ID hoặc slug.

```



---



### 4.5 Workbench đang tạo dữ liệu nghiệp vụ giả



Không được tự tạo hoặc mặc định:



```text

fake canonical asset

fake variant

fake taxonomy

unit "cái"

currency VND

supplier quote bằng 0

quote status active

```



khi backend không trả dữ liệu đó.



Yêu cầu:



```text

Missing data phải giữ null hoặc hiển thị empty state.

Không được biến missing price thành 0.

Market Quote và Appraised Price phải luôn tách biệt.

```



---



### 4.6 Excel intake chưa có giới hạn tài nguyên thật



Không được tiếp tục sử dụng cách:



```python

file.file.read()

list(ws.iter_rows(...))

```



mà không giới hạn kích thước.



Yêu cầu:



```text

Streaming row iteration.

File-size limit.

Row limit.

Column limit.

Cell-length limit.

Không silent truncate khi vượt 5.000 dòng.

Không xóa staging cũ trước khi upload mới parse thành công.

Duplicate header không được làm mất raw cell.

Sai sheet phải báo lỗi, không âm thầm chuyển sheet.

Không formula/macro/external link execution.

```



---



### 4.7 CI và tài liệu không phản ánh repository thực tế



Hiện default branch có thể vẫn trỏ về Sprint 0 và head commit chưa có workflow run.



Yêu cầu:



```text

Có main/default branch đúng.

Có PR workflow.

Có required quality gates.

Có PostgreSQL migration smoke.

Có backend tests.

Có frontend lint/build/vitest.

Có security and secret scans.

Audit không được tuyên bố PASS khi CI chưa chạy.

```



---



## 5. Remediation PR breakdown bắt buộc



Không được triển khai toàn bộ remediation trong một PR.



Phải thực hiện đúng thứ tự:



```text

S12-R-001 — Repository Baseline & CI Gate Repair

S12-R-002 — Authentication Identity Boundary Hardening

S12-R-003 — Workbench Project & Session Tenant Scoping

S12-R-004 — Official Mutation Command & Atomic Audit Gate

S12-R-005 — Dynamic Project Context & Live Workbench Data Integrity

S12-R-006 — Excel Intake Streaming & Transaction Hardening

S12-R-007 — Documentation Reconciliation & Final Acceptance

```



Mỗi PR phải:



```text

một trách nhiệm chính

diff nhỏ và reviewable

tests đi cùng implementation

không cleanup ngoài phạm vi

có audit report riêng

có rollback/migration impact

```



---



# 6. Nhiệm vụ hiện tại: chỉ thực hiện S12-R-001



## S12-R-001 — Repository Baseline & CI Gate Repair



Không triển khai R-002 đến R-007 trong lần thực hiện này.



### 6.1 Mục tiêu



Thiết lập baseline GitHub và CI đáng tin cậy trước khi sửa các security/business boundaries.



### 6.2 Preflight Git



Chạy và báo cáo:



```bash

git status --short

git branch --show-current

git log --oneline --decorate -10

git remote -v

git fetch --all --prune

```



Xác nhận:



```text

working tree có sạch không

branch hiện tại

baseline commit

remote repository

main branch có tồn tại không

default branch hiện tại là gì

```



Nếu working tree có thay đổi không liên quan, không được tự động stage hoặc xóa.



### 6.3 Branch



Tạo branch:



```text

s12-r-001-repository-ci-gate-repair

```



từ:



```text

s12-pr-002-excel-file-upload-parser-intake

```



hoặc từ commit baseline tương ứng nếu branch đã thay đổi.



Không bắt đầu từ nhánh Sprint 0.



### 6.4 CI requirements


