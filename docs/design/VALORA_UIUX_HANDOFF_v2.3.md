# VALORA — UI/UX Handoff v2.3

**Tài liệu thiết kế quy trình người dùng — Single-user Workflow**  
**Visual baseline:** Microsoft Fluent 2, desktop-first, data-heavy/table-first, Vietnamese-first  
**Trạng thái:** Canonical master — Consolidated v2.3  
**Cập nhật:** 31/08/2026

> Design authority không đồng nghĩa product code đã implement. Quyết định explicit mới hơn thắng trong đúng scope.

## 0. Authority hiện hành
Đã khóa các authority trước, Publishing simplified flow 3 bước và **`Quản lý Kho tri thức — Iteration 1`**. Không có S14, Kiểm tra hồ sơ riêng, KSCL/phê duyệt nhiều cấp, NCCQ aggregate trung gian hoặc màn rule-check giá riêng.

## 1. North-star flow
```text
Trang chủ → Quản lý yêu cầu sơ bộ → Tạo yêu cầu sơ bộ → Upload & Mapping Excel
→ Phân tích danh mục → Rà soát tích hợp → Tạo file kết quả sơ bộ
→ Chuyển sang thẩm định chính thức → Tổng quan hồ sơ
→ Xác nhận & điều chỉnh danh mục → Workbench tài sản [Asset Context Drawer theo ngữ cảnh]
→ Nguồn giá & Chứng cứ → Tạo & quản lý báo giá NCC
→ Hoàn tất từng báo giá NCC → Chọn NCC đã xác nhận giá → Kết quả thẩm định giá
→ Microsoft 365 Document Workspace
   → Tạo & Xem lại bộ tài liệu hồ sơ
      → Batch generation → Review
      → khi dữ liệu thay đổi: Bulk Sync loop
      → Tải lên mẫu tùy biến → AI mapping → Test fill → Xác nhận & Lưu template
   → Báo cáo / Chứng thư: child-flow chuyên sâu khi cần
   → Publishing
      → Chuẩn bị bộ phát hành
      → Xem lại & xử lý ngoại lệ
      → Xác nhận phát hành [commit boundary]
      → Release Manifest + khóa revision + audit [system consequence]

Supporting module, không phải checkpoint bắt buộc:
Quản lý Kho tri thức
  ↔ Workbench tra cứu Kho tri thức
  ← candidate từ Asset Identity / hồ sơ cũ / knowledge review
```

## 2. Price & Evidence
`Giá khảo sát Internet → Thuyết minh đơn giá → Giá Kết quả thẩm định giá hồ sơ cũ`. Giá NCC không phải nguồn chính. NCC thấp hơn đơn giá hiện hành luôn Warning; chênh tuyệt đối >15% Warning; không Blocking. Dữ liệu trong Kho tri thức chỉ là hỗ trợ/tra cứu và không override price-source authority này.

## 3. Kết quả thẩm định giá
03 bảng công ty immutable; giữ tên/thứ tự cột, Tổng cộng, Làm tròn, số tiền bằng chữ.

## 4. Knowledge Management — Baseline Iteration 1

### 4.1 Vai trò
`Quản lý Kho tri thức` là workspace quản trị/review độc lập với panel `Kho tri thức` trong Workbench.

- Panel Workbench = tra cứu/consumer surface theo tài sản đang chọn.
- Quản lý Kho tri thức = quản lý canonical assets, variants, aliases, candidates, historical dossiers và lineage/version.

### 4.2 IA baseline
```text
Tài sản chuẩn | Cần rà soát | Hồ sơ cũ | Lịch sử & nguồn gốc
```

- `Tài sản chuẩn`: Canonical Asset / Variant / Alias / structured KTKT / source-lineage.
- `Cần rà soát`: identity/contextual-alias/knowledge candidates cần human decision.
- `Hồ sơ cũ`: historical paired dossiers và knowledge candidates; không direct inject active knowledge.
- `Lịch sử & nguồn gốc`: source/file/locator, version, confirmed actor/time, superseded/current, usage history.

### 4.3 Layout baseline — Tài sản chuẩn
Desktop Fluent 2:
- trái: danh sách tài sản chuẩn + search/filter/status;
- giữa: chi tiết tài sản;
- phải: `Xem trước theo Báo cáo thẩm định giá` + thông tin quản trị.

Chi tiết tài sản gồm tabs:
`Thông tin chung | Đặc điểm KTKT | Biến thể | Alias | Nguồn gốc & phiên bản`.

### 4.4 Structured Đặc điểm KTKT
`Đặc điểm kinh tế - kỹ thuật` không được quản lý chỉ dưới dạng một chuỗi mô tả dài. VALORA phải hỗ trợ dữ liệu có cấu trúc, ví dụ:

- General/identity: Thương hiệu, Xuất xứ, Mã sản phẩm/model, Loại thiết bị.
- Technical attributes theo nhóm phù hợp từng loại tài sản.

Conceptual attribute shape:
`group | attribute name | value | unit | ordering | source/lineage`.

Không hard-code schema riêng cho TV; từng loại tài sản có thể có bộ thuộc tính khác nhau.

### 4.5 Preview và presentation authority của Báo cáo
Chi tiết tài sản có `Xem trước theo Báo cáo thẩm định giá`, chỉ view-only; không fake Word editor.

Preview phải phản ánh cấu trúc Báo cáo công ty:
`Tên tài sản | Đặc điểm kinh tế - kỹ thuật | Đvt | SL`.

Trong cột KTKT, presentation mapping theo hierarchy công ty:
```text
– Thuộc tính cấp 1: Giá trị.
– Thuộc tính cấp 1: Giá trị.
– Thông số kỹ thuật:
    + Thuộc tính: Giá trị.
    + Thuộc tính: Giá trị.
```

VALORA quản lý structured business data; template công ty/Microsoft 365 quản lý presentation.

Document generation/fill phải giữ theo template: table/column labels, font/size, alignment/indentation, `–`/`+`, line spacing, cell widths, borders, row/page continuation, page layout và pagination. Nội dung dài có thể chạy sang trang tiếp theo đúng template nhưng không được chuyển thành card hoặc free-form layout khác.

### 4.6 Human/AI boundary
AI được extract/normalize/suggest/group/explain/rerank; không được silent activate knowledge, không overwrite raw observation, không đổi company presentation authority. Official knowledge activation cần committed human decision.

### 4.7 Code-base alignment
UI surface này phải bám các domain boundary đã có: Column Mapping Memory, Raw Asset Observation, Asset Identity Memory, CanonicalAsset, AssetVariant, AssetAlias, ContextualAssetAlias, IdentityCandidate, SimilarityScore, IdentityReviewItem, IdentityDecisionLog, DossierBundle, DossierRowAlignment và reviewed quote/spec/knowledge candidates. Direct active-knowledge injection bị cấm.

## 5. Template / AI / Spreadsheet
AI advisory; user xác nhận mapping/template. Không silent accept/publish/overwrite/change formula. Custom field không tự promote canonical. Fill Engine giữ authority hiện hành và phải tôn trọng presentation mapping của structured KTKT khi fill Báo cáo.

## 6. Microsoft 365 Document Workspace
VALORA quản lý structured data, Data Snapshot, lineage, audit, sync status, Release Manifest. Microsoft 365 quản lý Word/file/file version. `Document Revision != Microsoft 365 file version`.

### 6.1 Document Set / Bulk Sync / Custom Template — Baseline
Các baselines hiện hành tiếp tục có hiệu lực. Bulk Sync preview/conflict zero-write; Confirm & Sync là write boundary; result theo từng tài liệu. Không export PDF.

### 6.2 Báo cáo & Chứng thư
Giữ Generation/Sync + Managed Regions baselines riêng; Document Set là orchestration layer. Báo cáo sử dụng structured KTKT nhưng presentation do template công ty quản lý.

### 6.3 Publishing — Simplified Baseline hoàn chỉnh
```text
Chuẩn bị bộ phát hành
→ Xem lại & xử lý ngoại lệ
→ Xác nhận phát hành [commit boundary]
→ Release Manifest + khóa revision + audit [system consequence]
```
Không UI `Khóa phiên bản` riêng. Không `Xuất PDF`.

#### 6.3.1 Chuẩn bị bộ phát hành — Baseline Iteration 1
Exception-first. VALORA auto-select revision mới nhất đủ điều kiện; user chủ yếu xử lý ngoại lệ. Auto-select không auto-publish.

#### 6.3.2 Xem lại & xử lý ngoại lệ — Baseline Iteration 1
Ready không phải task. Blocking phải sửa/revalidate hoặc loại khỏi release. Warning không tự Blocking; giữ và phát hành phải là explicit decision. Màn này chưa publish/finalize/lock.

#### 6.3.3 Xác nhận phát hành — Baseline Iteration 1
Final commit/write boundary. Blocking=0; mandatory exceptions resolved; revision valid; release plan not stale; no unresolved version conflict; readiness true. Success creates final Release Manifest, locks bound revisions and records audit/lineage.

### 6.4 Release semantics
Published Release và các Document Revision đã bind là immutable. Muốn thay đổi sau phát hành phải tạo release mới; không mutate release cũ.

## 7. Guardrails
- Single-user; AI advisory.
- Vietnamese-first, Fluent 2, desktop-first, data-heavy/table-first.
- Exception-first UX ở Publishing.
- Auto-select nhưng không auto-publish.
- Không silent bypass Blocking/Warning/publish/overwrite/knowledge activation.
- Không fake Word/Excel editor.
- Không export PDF trong Bulk Sync Result hoặc Publishing.
- Structured KTKT = business data; presentation = company template authority.
- Historical knowledge không override price-source authority.
- Published revision/release immutable.
- Một primary CTA mỗi context.

## 8. Capability inventory
| Capability | Trạng thái |
|---|---|
| S09–S13 / NCCQ / Result | P0 baseline |
| **Quản lý Kho tri thức** | **P0 baseline Iteration 1** |
| Structured KTKT + report preview mapping | **P0 baseline Iteration 1** |
| Microsoft 365 Document Workspace | P0 baseline |
| Tạo & Xem lại bộ tài liệu hồ sơ | P0 baseline Iteration 1 |
| Bulk Sync loop | P0 baseline Iteration 1 |
| AI custom template + Confirm/Save | P0 baseline Iteration 1 |
| Managed Regions / Generation-Sync Báo cáo & Chứng thư | P0 baseline |
| Chuẩn bị bộ phát hành | P0 baseline Iteration 1 |
| Xem lại & xử lý ngoại lệ | P0 baseline Iteration 1 |
| Xác nhận phát hành | P0 baseline Iteration 1 |
| Publishing simplified flow | P0 baseline complete |
| Spreadsheet Fill Engine | P0 baseline |

## 9. Companion authority
- `VALORA_UIUX_HANDOFF_v2.3_KNOWLEDGE_MANAGEMENT_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_RELEASE_CONFIRMATION_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_RELEASE_EXCEPTION_REVIEW_BASELINE_ADDENDUM.md`.
- `VALORA_UIUX_HANDOFF_v2.3_RELEASE_PREPARATION_BASELINE_ADDENDUM.md`.
- Các addendum Bulk Sync, Custom Template, Document Set, Generation/Sync, Managed Regions, Sync-Version, Fill Engine, NCC warning, Result/NCCQ hiện hành tiếp tục có hiệu lực.

## 10. ADR
Nếu implementation thay đổi canonical/variant/attribute persistence, knowledge activation/versioning, attribute grouping/order, source lineage, presentation mapping/Managed Region merge semantics, Release Manifest transaction boundary, locking atomicity, retry/idempotency, failure recovery hoặc partial-publish semantics thì phải đánh giá ADR riêng trước khi sửa product code.
