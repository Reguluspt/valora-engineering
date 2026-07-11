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



Cập nhật GitHub Actions để chạy trên:



```yaml

pull_request:

push:

  branches:

    - main

    - "s12-*"

```



Các job tối thiểu:



#### Backend



```text

Python version thống nhất với pyproject và Dockerfile.

Install dependencies từ backend.

Run ruff/check phù hợp.

Run pytest.

```



#### PostgreSQL integration



Dùng PostgreSQL service container.



Chạy:



```text

Alembic upgrade từ empty database lên head.

Kiểm tra migration graph chỉ có một head.

Chạy nhóm persistence/integration tests phù hợp.

```



Không dùng riêng SQLite để kết luận PostgreSQL migration PASS.



#### Frontend



Nếu có `package-lock.json`, dùng:



```bash

npm ci

```



Chạy:



```bash

npm run lint

npm run build

npx vitest run --globals

```



Nếu test script chưa có trong package.json, bổ sung script rõ ràng thay vì bỏ test.



#### Worker



Chạy:



```bash

pytest

```



và các lint/check phù hợp nếu worker đang nằm trong repository.



#### Security



Thêm gate cho:



```text

secret scanning

Python dependency vulnerability scan

Node dependency vulnerability scan

repository security policy script

```



Không ghi secret thật vào workflow.



Không cho phép security scanner chỉ in warning rồi exit 0 khi phát hiện vấn đề blocking.



### 6.5 Sửa security scanner hiện tại



Kiểm tra:



```text

backend/tests/check_security.py

```



Đánh giá lại các forbidden patterns.



Không được giữ rule đã lỗi thời khiến endpoint hợp lệ hiện tại bị báo false positive.



Scanner phải tập trung vào các lỗi thực tế, ví dụ:



```text

production X-User-Id authentication

all-zero UUID hard-code

hard-coded project slug trong runtime component

plaintext production secrets

dangerous wildcard production CORS

direct official mutation routes chưa được allowlist

```



Không được viết scanner chỉ để test hiện tại pass.



### 6.6 Default branch và branch protection



Nếu có quyền GitHub:



```text

Tạo/xác nhận main.

Đặt main làm default branch.

Đề xuất hoặc cấu hình branch protection.

Đặt required checks theo tên CI job thực tế.

```



Nếu Antigravity không có quyền thay đổi repository settings:



```text

Không được giả vờ đã thay đổi.

Tạo tài liệu chính xác các bước owner phải thực hiện.

Ghi trạng thái PASS WITH LIMITATION.

```



### 6.7 Không được làm trong R-001



Không được sửa:



```text

authentication business implementation

Workbench session scoping implementation

Human commit behavior

Excel parser

Validation Engine

Frontend project context

Domain models ngoài nhu cầu CI

```



Chỉ được sửa code ngoài phạm vi khi bắt buộc để CI chạy, và phải giải thích rõ.



---



## 7. Acceptance criteria của S12-R-001



PR chỉ được kết luận PASS khi:



```text

CI chạy trên pull request.

Backend tests chạy.

Frontend lint/build/vitest chạy.

Worker tests chạy.

PostgreSQL migration từ empty DB chạy.

Migration graph có một head.

Security scanner được CI gọi.

Dependency scan được CI gọi.

Head commit có workflow run.

Default branch không còn là nhánh Sprint 0.

Required checks có thể dùng làm branch protection.

Không có secret mới.

Không triển khai phạm vi R-002 trở đi.

```



Nếu chưa thể đổi default branch hoặc branch protection do thiếu GitHub permission:



```text

Final status tối đa là PASS WITH LIMITATION.

Phải cung cấp hướng dẫn owner thực hiện.

Không được báo PASS tuyệt đối.

```



---



## 8. Test failure policy



Nếu một test fail:



1. Xác định lỗi là regression thật hay test cũ sai.

2. Không xóa hoặc skip test chỉ để CI xanh.

3. Không giảm assertion.

4. Không chuyển security failure thành warning.

5. Sửa root cause hoặc ghi rõ blocker có bằng chứng.



Nếu dependency hoặc environment thiếu:



```text

Cài đặt dependency cần thiết.

Chạy lại.

Ghi rõ command và kết quả.

```



---



## 9. Quy tắc code và security bắt buộc



```text

Không invent domain behavior.

Không bypass tenant boundary.

Không official data mutation ngoài audit path.

Không auto-approval.

Không AI commit.

Không hard-code user/project/organization/session.

Không plaintext production secrets.

Không raw stack trace/local path/internal token cho user.

Không unrelated refactor.

Không xóa guardrail.

Không sửa audit cũ để che lỗi.
