# VALORA UI/UX v2.3 — Authority Index

**Status:** Canonical UI/UX reading order for v2.3  
**Purpose:** Ngăn iteration/addendum cũ override quyết định hiện hành.  
**Consolidation:** v2.3 — cập nhật `Sinh & Đồng bộ Chứng thư thẩm định giá — Iteration 1` ngày 31/08/2026.

## 1. Thứ tự đọc hiện hành
1. `VALORA_UIUX_HANDOFF_v2.3.md` — canonical master.
2. `VALORA_UIUX_HANDOFF_v2.3_CERTIFICATE_GENERATION_SYNC_BASELINE_ADDENDUM.md` — **Baseline / Design Authority `Sinh & Đồng bộ Chứng thư thẩm định giá — Iteration 1`**.
3. `VALORA_UIUX_HANDOFF_v2.3_REPORT_GENERATION_SYNC_BASELINE_ADDENDUM.md` — Baseline `Sinh & Đồng bộ Báo cáo thẩm định giá — Iteration 1`.
4. `VALORA_UIUX_HANDOFF_v2.3_SPREADSHEET_FILL_ENGINE_BASELINE_ADDENDUM.md` — Baseline Fill Engine.
5. `VALORA_UIUX_HANDOFF_v2.3_NCC_PRICE_WARNING_RULE_ADDENDUM.md` — current NCC price warning authority.
6. `VALORA_UIUX_HANDOFF_v2.3_MANAGED_REGIONS_CERTIFICATE_BASELINE_ADDENDUM.md` — Baseline Managed Regions — Chứng thư.
7. `VALORA_UIUX_HANDOFF_v2.3_DOCUMENT_PUBLISH_BASELINE_ADDENDUM.md` — Baseline Publishing.
8. `VALORA_UIUX_HANDOFF_v2.3_DOCUMENT_SYNC_VERSION_BASELINE_ADDENDUM.md` — Baseline Sync/Version.
9. `VALORA_UIUX_HANDOFF_v2.3_MANAGED_REGIONS_REPORT_BASELINE_ADDENDUM.md` — Baseline Managed Regions — Báo cáo.
10. `VALORA_UIUX_HANDOFF_v2.3_CONTRACT_DOCUMENT_WORKSPACE_BASELINE_ADDENDUM.md` — Baseline 03_Hợp đồng.
11. Các addendum Template/AI/Result/NCCQ hiện hành trong scope tương ứng.
12. `VALORA_USER_FLOW_MINDMAP_v2.3.md` — support flow; không override master.

## 2. Routing authority
```text
... → Kết quả thẩm định giá
→ Microsoft 365 Document Workspace
   → 03_Hợp đồng
   → Báo cáo thẩm định giá
      → Sinh & Đồng bộ Báo cáo
      → Managed Regions — Báo cáo
   → Chứng thư thẩm định giá
      → Sinh & Đồng bộ Chứng thư
         → Chọn template & phạm vi
         → Data Snapshot
         → Preview & Review vùng
         → Tạo Document Revision
         → Đồng bộ Microsoft 365
         → Kết quả đồng bộ
      → Managed Regions — Chứng thư
   → Đồng bộ dữ liệu & Quản lý phiên bản
   → Phát hành bộ tài liệu
```

## 3. Price & Evidence authority
```text
1. Giá khảo sát từ Internet
2. Thuyết minh đơn giá
3. Giá trong phần Kết quả thẩm định giá của hồ sơ cũ
```
Giá NCC không phải nguồn chính xác định đơn giá thẩm định cuối cùng.

Cảnh báo NCC: `Giá NCC < Đơn giá hiện hành` luôn Warning; `|Giá NCC - Đơn giá hiện hành| / Đơn giá hiện hành > 15%` là Warning chênh lệch lớn. Warning không Blocking; không có màn rule-check riêng.

## 4. Baseline visual authority
- NCCQ — Iteration 6.
- Kết quả thẩm định giá — Iteration 1.
- Microsoft 365 Document Workspace — baseline.
- 03_Hợp đồng — Iteration 1.
- Managed Regions — Báo cáo — Iteration 1.
- Managed Regions — Chứng thư — Iteration 1.
- Sync/Version — Iteration 1.
- Publishing — Iteration 1.
- Fill Engine — Iteration 1.
- Sinh & Đồng bộ Báo cáo — Iteration 1.
- **Sinh & Đồng bộ Chứng thư — Iteration 1.**

## 5. Document Workspace authority
Managed Regions status: `Đã đồng bộ / Cần cập nhật / Bạn tự chỉnh trong Word / Lỗi`.

### 5.1 Document Generation/Sync shared contract
Báo cáo và Chứng thư dùng chung mental flow:
```text
Chọn template & phạm vi → Data Snapshot → Preview & Review vùng → Tạo Document Revision → Đồng bộ Microsoft 365 → Kết quả đồng bộ
```
Preview view-only; không fake Word editor. `Tạo Document Revision` là explicit action. Readiness trước sinh có thể là `Đã mapping / Cần xem / Chưa mapping`; không thay thế Managed Regions status sau khi Word tồn tại.

Lineage:
```text
Template Version → Data Snapshot → Document Revision → Microsoft 365 file/version
```
Không silent đổi template/snapshot, overwrite, sync hoặc publish. Region/field trên visual chỉ minh họa, không hard-code schema. Conflict trong Managed Region phải xem/xử lý trước khi ghi; narrative ngoài vùng giữ nguyên.

### 5.2 Chứng thư
Child flow Chứng thư dùng authority Managed Regions — Chứng thư sau khi revision/file Word tồn tại. Không tạo lifecycle song song với Sync/Version/Publishing.

## 6. Bảng tính authority
Reference `Bang Tinh - HĐ 42.xlsx`: `Hn = MIN(En:Gn)`; `In = Dn*Hn`. Fill Engine không overwrite template, không staticize formula, không silent drop workbook feature.

## 7. Guardrail
- Single-user; AI advisory.
- Không S14, màn Kiểm tra hồ sơ, KSCL workflow riêng hoặc màn Kiểm tra quy tắc đối chiếu giá.
- Không fake Word/Excel editor.
- Không silent accept/sync/overwrite/publish.
- Document Revision != Microsoft 365 file version.
- Revision/release đã phát hành immutable.
- Vietnamese-first; một primary CTA mỗi context.

## 8. ADR
Nâng `Sinh & Đồng bộ Chứng thư thẩm định giá — Iteration 1` thành baseline là UI/UX authority update. Thay đổi persistence, transaction boundary, conflict detection, managed-region write policy hoặc Microsoft 365 version binding khi implement phải đánh giá ADR riêng.
