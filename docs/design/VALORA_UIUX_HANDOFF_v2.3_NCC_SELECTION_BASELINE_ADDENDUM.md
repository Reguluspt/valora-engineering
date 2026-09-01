# VALORA UI/UX Handoff v2.3 — NCC Selection Baseline Addendum

**Baseline:** `Chọn NCC đã xác nhận giá — Iteration 1`  
**Status:** Design Authority / Baseline  
**Date:** 01/09/2026  
**Parent authority:** `VALORA_UIUX_HANDOFF_v2.3.md`

## 1. Purpose
`Chọn NCC đã xác nhận giá` là checkpoint sau `Hoàn tất từng báo giá NCC` và trước `Kết quả thẩm định giá` trong north-star flow. Mục tiêu là ghi nhận NCC/báo giá đã được người dùng xác nhận cho từng dòng tài sản của hồ sơ.

Baseline này không biến giá NCC thành appraisal-price authority và không tạo lại NCCQ aggregate trung gian.

## 2. UI/Data Contract v1
Selection scope:
```text
1 Project + 1 ProjectAssetLine + 1 confirmed QuoteLine = 1 current NCC Selection
```

Không đặt trạng thái `selected` toàn cục trên Supplier hoặc QuoteLine. Selection là project-line context và phải giữ lịch sử/revision.

### 2.1 Eligibility
Một candidate chỉ được chọn khi:
- thuộc đúng dòng tài sản;
- NCC xác định được;
- đơn giá hợp lệ;
- báo giá đã hoàn tất/xác nhận giá;
- evidence/source còn truy xuất được.

Warning không Blocking. Quote chưa hoàn tất hoặc evidence lỗi thì không eligible.

### 2.2 Read aggregate
UI cần aggregate theo dòng tài sản gồm tối thiểu:
- asset: tên tài sản, ĐVT, SL, đơn giá hiện hành;
- candidates: supplier, quote batch/revision, quote line, giá NCC, currency, quote date, evidence, eligibility, difference amount/percent, warnings;
- current selection: selection id, selected quote/supplier, confirmed price snapshot, actor/time, revision, stale flag.

Frontend không tự tạo selection/warning state bằng local state nếu backend chưa trả contract tương ứng.

### 2.3 Warning authority
Với `C = đơn giá hiện hành`, `S = giá NCC`:
```text
Δ = S - C
Δ% = Δ / C × 100
```

UI phải hiển thị:
`Đơn giá hiện hành | Giá NCC | Chênh lệch | Chênh lệch % | Warning`.

Rules:
- `S < C` → luôn Warning;
- `abs(Δ) / C > 15%` → Warning;
- `S > 115% × C` → Warning;
- Warning không Blocking.

Nếu `C = 0` hoặc chưa có thì `difference_percent = null`; không tạo phần trăm giả.

## 3. Write boundary
Primary CTA: **`Xác nhận NCC đã chọn`**.

Đây là explicit human commit. Server phải tự resolve lại QuoteLine/Supplier/QuoteBatch/price/warnings; không tin monetary values do frontend gửi.

Conceptual command:
```text
POST /projects/{project_id}/asset-lines/{line_id}/ncc-selection
```

Payload tối thiểu:
```json
{
  "quote_line_id": "...",
  "expected_selection_revision": 3,
  "acknowledged_warning_codes": ["..."]
}
```

Conflict khi expected revision không còn hiện hành phải trả 409 và yêu cầu tải lại/xác nhận lại; không last-write-wins.

## 4. Snapshot, revision, stale semantics
Khi xác nhận phải giữ tối thiểu supplier/quote identifiers, supplier name snapshot, QuoteBatch revision, quoted price/currency/date snapshot, evidence/source reference, current unit price snapshot, difference/warning snapshot, actor/time và selection revision.

Đổi NCC tạo selection revision mới; không overwrite lịch sử cũ.

Nếu QuoteBatch/QuoteLine nguồn tạo revision mới sau khi đã chọn:
```text
selection cũ KHÔNG auto-rebind
→ status = Cần xem lại
→ user explicit xác nhận lại
```

Audit events tối thiểu:
`NCC_SELECTION_CONFIRMED | NCC_SELECTION_CHANGED | NCC_SELECTION_RECONFIRMED | NCC_SELECTION_MARKED_STALE`.

## 5. Downstream boundary
NCC Selection được dùng cho:
- tạo/tái tạo báo giá NCC;
- đối chiếu báo giá NCC;
- xác định NCC đã chọn trong bảng báo giá;
- evidence/audit/lineage.

Không được tự động:
- ghi đè đơn giá thẩm định;
- tạo/sửa `AppraisedPriceDecision`;
- thay đổi giá trong `Kết quả thẩm định giá`;
- thay đổi price-source priority.

Price authority giữ nguyên:
`Giá khảo sát Internet → Thuyết minh đơn giá → Giá Kết quả thẩm định giá hồ sơ cũ`.

`NCC selected ≠ appraised price selected`.

## 6. Visual baseline — Iteration 1
Desktop-first, Fluent 2, Vietnamese-first, data-heavy/table-first.

Main surface:
- KPI summary: tổng dòng tài sản, đã chọn NCC, chưa chọn, cần xem lại, tổng báo giá đủ điều kiện;
- filter/search;
- table: `STT | Tên tài sản | ĐVT | SL | Đơn giá hiện hành | NCC đã chọn | Giá NCC đã chọn | Chênh lệch | Chênh lệch % | Cảnh báo | Trạng thái`;
- footer selection actions;
- right drawer `Chi tiết dòng tài sản`.

Drawer tối thiểu:
- asset summary;
- tabs `Danh sách báo giá đủ điều kiện | Thông tin chọn hiện tại | Lịch sử chọn`;
- eligible quote table with one selectable candidate;
- selected quote detail + evidence link;
- price comparison + warning summary;
- primary CTA `Xác nhận NCC đã chọn cho dòng này`.

Visual authority là đúng mockup `Chọn NCC đã xác nhận giá — Iteration 1` được người dùng duyệt ngày 01/09/2026.

## 7. Guardrails
- Single-user; AI không auto-select NCC.
- Warning non-blocking nhưng phải hiển thị trước commit.
- Không silent rebind sau quote revision.
- Không NCCQ aggregate trung gian.
- Không màn rule-check giá riêng.
- Không dùng NCC Selection để quyết định/ghi đè giá thẩm định.
- Một primary CTA mỗi context.
