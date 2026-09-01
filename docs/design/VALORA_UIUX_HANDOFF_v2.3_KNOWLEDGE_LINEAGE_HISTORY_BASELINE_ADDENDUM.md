# VALORA UI/UX v2.3 — Knowledge Lineage History Baseline Addendum

**Baseline:** `Lịch sử & nguồn gốc — Iteration 1`  
**Status:** Design Authority / Baseline  
**Date:** 01/09/2026

## 1. Scope
`Lịch sử & nguồn gốc` là read-oriented traceability surface trong workspace `Quản lý Kho tri thức`, không phải checkpoint mới trong north-star flow và không tạo audit/version subsystem mới.

IA giữ nguyên:
`Tài sản chuẩn | Cần rà soát | Hồ sơ cũ | Lịch sử & nguồn gốc`.

Màn hình chiếu dữ liệu từ các primitive hiện hữu như `IdentityDecisionLog`, `KnowledgeVersion`, `KnowledgeLineage`, historical dossier/source locators và các review decisions liên quan.

## 2. Layout baseline
Desktop-first, Microsoft Fluent 2, Vietnamese-first, data-heavy/table-first.

### 2.1 Filter area
- Tìm kiếm toàn lịch sử.
- Loại tri thức.
- Tài sản chuẩn.
- Loại sự kiện.
- Nguồn.
- Trạng thái phiên bản.
- Khoảng thời gian.

Không expose technical identifiers như `target_id`, `row_version` cho người dùng nghiệp vụ.

### 2.2 Main history table
Các cột authority:
`Thời điểm | Tài sản / Tri thức | Nội dung thay đổi | Nguồn | Quyết định | Phiên bản | Người thao tác | Trạng thái`.

Event labels dùng ngôn ngữ nghiệp vụ, ví dụ `Xác nhận đặc điểm KTKT`, `Thêm alias`, `Tạo phiên bản mới`, `Phiên bản bị thay thế`, `Tạo từ hồ sơ cũ`; không hiển thị raw event codes làm nhãn chính.

### 2.3 Detail drawer
Chọn một dòng mở drawer `Chi tiết lịch sử`, read-only, gồm tối thiểu:
1. `Thay đổi` — before → after hoặc proposed → confirmed khi có dữ liệu.
2. `Nguồn gốc` — hồ sơ/source file và locator page/sheet/table/row/cell khi có.
3. `Quyết định` — decision, reason/note, actor, time; AI/system chỉ được thể hiện là đề xuất/hệ thống, không impersonate human decision.
4. `Phiên bản & Sử dụng` — phiên bản hiện hành, phiên bản bị thay thế và nơi đang tham chiếu khi usage reference tồn tại.

## 3. Chuỗi nguồn gốc
Lineage chain được trình bày trong drawer/tab, không biến toàn màn hình thành graph:

`Hồ sơ / nguồn gốc → File → Vị trí dữ liệu → Dữ liệu trích xuất → Candidate → Quyết định rà soát → Knowledge Version → Tài sản chuẩn / Variant / KTKT`.

Các mắt xích không có dữ liệu phải được thể hiện là không khả dụng/chưa ghi nhận, không suy diễn hoặc tạo lineage giả.

## 4. Actions
Đây là history/traceability surface nên không có commit CTA.

Contextual navigation actions được phép:
- `Xem nguồn gốc đầy đủ`.
- `Mở hồ sơ cũ`.
- `Mở tài sản chuẩn`.
- `Xem quyết định rà soát`.

Không cho phép edit/delete audit entry, restore/rollback, approve, activate knowledge hoặc silent overwrite từ màn hình này.

## 5. Boundary với lịch sử giá
Timeline giá trong `Nguồn giá & Chứng cứ`/asset-case context tiếp tục là lịch sử nghiệp vụ theo hồ sơ/tài sản. `Lịch sử & nguồn gốc` là knowledge-governance history xuyên `Quản lý Kho tri thức`. Có thể deep-link giữa hai context khi phù hợp nhưng không duplicate hai capability.

## 6. Human / AI boundary
- AI/rules có thể extract/normalize/retrieve/score/align/explain/suggest.
- Official knowledge và review decision vẫn yêu cầu explicit human decision theo authority hiện hành.
- Không auto-approve, auto-activate, auto-restore hoặc sửa history.
- Audit/lineage là append-oriented/immutable theo semantics hiện hành.

## 7. Approved mockup authority
Mockup được người dùng chốt ngày 01/09/2026 với tiêu đề `Lịch sử & nguồn gốc — Iteration 1` là visual authority cho baseline này. Khi đưa vào master DOCX Part 2 phải dùng đúng mockup đã duyệt, không tự thiết kế lại.

## 8. Implementation note
Baseline này không yêu cầu persistence architecture mới. Nếu implementation cần thay đổi semantics/persistence của `KnowledgeLineage`, `KnowledgeVersion`, `IdentityDecisionLog`, source locator hoặc usage-reference model thì phải lập ADR trước khi thay đổi architecture.
