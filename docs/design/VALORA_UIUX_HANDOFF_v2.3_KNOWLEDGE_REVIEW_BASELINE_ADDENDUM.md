# VALORA UI/UX Handoff v2.3 — Cần rà soát tri thức — Baseline Addendum

**Status:** Baseline / Design Authority  
**Iteration:** 1  
**Date:** 31/08/2026  
**Parent:** `Quản lý Kho tri thức — Iteration 1`

## 1. Vai trò
`Cần rà soát tri thức` là human-review queue bên trong `Quản lý Kho tri thức`. Candidate do extraction, rules, AI, Asset Identity Memory hoặc hồ sơ cũ tạo ra không trở thành tri thức chính thức nếu chưa có quyết định của người dùng.

## 2. Routing
```text
Quản lý Kho tri thức
  → Cần rà soát
      → xem candidate + nguồn gốc + so sánh
      → Xác nhận | Chỉnh sửa rồi xác nhận | Không phù hợp | Để xử lý sau
      → ghi decision history/lineage
      → nếu xác nhận: tạo/cập nhật knowledge version theo contract hiện hành
```
Đây không phải approval workflow nhiều người.

## 3. Layout baseline
Desktop Fluent 2, data-heavy:
- header/breadcrumb giữ shell Kho tri thức;
- tabs `Tài sản chuẩn | Cần rà soát | Hồ sơ cũ | Lịch sử & nguồn gốc`, `Cần rà soát` active;
- trái: danh sách candidate, search/filter/sort, loại candidate, nguồn tạo, độ ưu tiên, trạng thái;
- giữa: candidate đang xem, structured data, tabs `Thông tin ứng viên | So sánh với kho tri thức | Nguồn gốc & lý do đề xuất | Xem trước theo Báo cáo`;
- phải: `Xem trước theo Báo cáo thẩm định giá` view-only, ghi chú nội bộ, lịch sử quyết định;
- footer decision bar.

## 4. Candidate types
UI hỗ trợ tối thiểu các loại: `Tài sản mới`, `Biến thể mới`, `Alias`, `Đặc điểm KTKT`, và knowledge candidate từ hồ sơ cũ. UI không được ép tất cả candidate thành một schema tài sản mới.

## 5. Decision semantics
Các quyết định:
1. `Xác nhận` — explicit human commit để đưa candidate hợp lệ vào knowledge lifecycle.
2. `Chỉnh sửa rồi xác nhận` — user sửa dữ liệu được phép trước khi commit; phải giữ candidate/source lineage và lưu giá trị đã xác nhận.
3. `Không phù hợp` — reject candidate; không xóa nguồn/candidate evidence.
4. `Để xử lý sau` — defer; candidate vẫn chưa được kích hoạt thành official knowledge.

Confidence/độ ưu tiên chỉ phục vụ sắp xếp và giải thích; không auto-approve dù confidence cao.

## 6. Structured KTKT + report preview
Candidate KTKT dùng structured attributes theo baseline Quản lý Kho tri thức. Preview Báo cáo là view-only và phải phản ánh presentation mapping công ty `Tên tài sản | Đặc điểm kinh tế - kỹ thuật | Đvt | SL`, hierarchy `–` / `+`. Preview không biến VALORA thành Word editor và không thay đổi authority của template công ty.

## 7. Source, comparison, lineage
Trước quyết định, user phải có thể xem nguồn gốc và lý do đề xuất; khi có tri thức hiện hữu phải có surface so sánh để tránh silent overwrite. Quyết định cần audit tối thiểu candidate, source/locator, giá trị trước/đề xuất/đã xác nhận khi áp dụng, quyết định, actor và thời điểm.

Raw observation/source evidence không bị ghi đè bởi normalize/review decision. Rejected/deferred candidate không được direct inject active knowledge.

## 8. Human/AI boundary
AI/rules được extract, normalize, retrieve, score, rerank, group, explain và đề xuất. Chỉ quyết định explicit của người dùng mới được kích hoạt tri thức chính thức. AI/system không impersonate human confirmation.

## 9. Guardrails
- Single-user; không approval nhiều cấp.
- Không auto-accept candidate.
- Không silent overwrite canonical/variant/alias/KTKT.
- Không xóa provenance khi reject.
- `Để xử lý sau` không được coi là đã xác nhận.
- Historical knowledge không override price-source authority v2.3.
- Một primary commit action trong context review; các action khác phải rõ semantic.

## 10. ADR-sensitive implementation
Nếu implementation thay đổi persistence của review queue, decision log, candidate lifecycle, knowledge activation/versioning, merge/conflict semantics, source lineage hoặc idempotency của confirm/reject/defer thì phải đánh giá ADR trước khi sửa product code.
