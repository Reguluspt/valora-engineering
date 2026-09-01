# VALORA UI/UX v2.3 — Tổng quan hồ sơ / Orchestration Hub Baseline Addendum

**Status:** DESIGN AUTHORITY / BASELINE  
**Baseline:** `Tổng quan hồ sơ — Orchestration Hub — Iteration 2`  
**Date:** 01/09/2026  
**Contract:** `Global Case State + Resume / Next-action Contract v1`

## 1. Vai trò
`Tổng quan hồ sơ` là project-level orchestration hub sau `Chuyển sang thẩm định chính thức`. Không tạo màn `Tiến độ hồ sơ` riêng.

Màn hình phải trả lời: hồ sơ đang ở đâu; đã hoàn tất gì; blocker/warning/stale nào cần chú ý; hành động tiếp theo là gì; khi quay lại nên resume ở đâu.

## 2. Global Case State projection
UI dùng project-level projection tổng hợp từ Project + WorkflowInstance + domain completion facts + ValidationIssue + document/release state + last meaningful context. Không lấy một enum đơn lẻ làm UI route authority và không để frontend tự suy luận state machine.

Canonical stages v1 gồm 16 stage:
`PRELIMINARY_REQUEST | PRELIMINARY_ANALYSIS | PRELIMINARY_READY | OFFICIAL_INTAKE | ASSET_REVIEW | ASSET_WORKBENCH | PRICE_EVIDENCE | SUPPLIER_QUOTES | SUPPLIER_SELECTION | APPRAISAL_RESULT | DOCUMENT_WORKSPACE | DOCUMENT_SYNC_REVIEW | PUBLISHING_PREPARATION | PUBLISHING_EXCEPTION_REVIEW | PUBLISHING_CONFIRMATION | PUBLISHED`.

UI hiển thị nhãn nghiệp vụ tiếng Việt; enum kỹ thuật chỉ là secondary/debug reference nếu thực sự cần.

## 3. Next-action
Một hồ sơ chỉ có một primary `next_action`. Next-action được derive từ business facts theo precedence:
1. Blocking bắt buộc;
2. stale state cần review;
3. công việc đang dở hợp lệ;
4. bước bắt buộc chưa hoàn tất gần nhất;
5. bước tiếp theo theo north-star;
6. Published/no action.

Khối `Hành động tiếp theo` không được gắn semantics `AI gợi ý`. AI chỉ giải thích/tóm tắt; AI không quyết định transition hoặc business commit.

Primary CTA của hub: `Tiếp tục xử lý` / contextual equivalent dẫn tới `next_action`. Warning không Blocking.

## 4. Resume
`Resume Target` ưu tiên last meaningful context nếu còn hợp lệ; nếu blocker/stale mới quan trọng hơn thì next-action thắng; context mất/stale thì fallback stage default. Last visited route không tự động là resume authority.

Meaningful context có thể là ProjectAssetLine, NCC Selection, document/revision, sync conflict hoặc publishing exception. Resume không phải completion/business commit và không bypass blocker.

## 5. Layout baseline — Iteration 2
Desktop Fluent 2, Vietnamese-first. Cấu trúc:
- header + thông tin hồ sơ;
- card `Trạng thái hồ sơ` với nhãn giai đoạn nghiệp vụ, completion, Blocking, Warning, Cần xem lại;
- `Tiến độ các bước bắt buộc` theo 16 canonical stages; có `Document Sync Review` và `Publishing Exception Review`;
- tiến độ chi tiết theo nhóm;
- `Vấn đề ngăn bước tiếp theo`;
- `Cảnh báo nổi bật`;
- thông tin chung + thống kê nhanh;
- right rail `Hành động tiếp theo`, `Ngữ cảnh hồ sơ (Resume Target)`, `Hoạt động gần đây`;
- một primary CTA trong next-action context.

Baseline visual approved in conversation: `Tổng quan hồ sơ — Orchestration Hub — Iteration 2`.

## 6. Invariants
- Tổng quan hồ sơ là orchestration hub, không phải approval dashboard.
- Không revive KSCL/QC/multi-level approval.
- Completion derive từ mandatory business facts, không từ màn đã mở.
- Supporting Knowledge Management không làm giảm completion.
- `current_stage` và `next_action.stage` có thể khác nhau khi cần quay lại xử lý blocker/stale.
- Không silent transition, silent stale reconciliation hoặc frontend-only state machine.
- Published release immutable.
- Một primary CTA mỗi context.

## 7. Implementation direction
Read projection conceptual endpoint: `GET /api/v1/projects/{project_id}/case-state`.
Resume persistence conceptual endpoint: `PUT /api/v1/projects/{project_id}/resume-context`.
Backend trả semantic route key; frontend sở hữu URL mapping. Concurrency dùng `case_version`/expected version phù hợp; stale conflict phải reload projection và explicit xử lý.
