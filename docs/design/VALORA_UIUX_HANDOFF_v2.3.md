# VALORA — UI/UX Handoff v2.3

**Tài liệu thiết kế quy trình người dùng — Single-user Workflow**  
**Visual baseline:** Microsoft Fluent 2, desktop-first, data-heavy/table-first, Vietnamese-first  
**Trạng thái:** Canonical master — Consolidated v2.3  
**Cập nhật:** 31/08/2026

> Design authority không đồng nghĩa product code đã implement. Quyết định explicit mới hơn thắng trong đúng scope.

## 0. Authority hiện hành
Đã khóa: S09–S13; Nguồn giá & Chứng cứ; NCCQ Iteration 6; Kết quả thẩm định giá; Microsoft 365 Document Workspace; Managed Regions Báo cáo/Chứng thư; Sync/Version; Publishing; Template/AI; Fill Engine; Sinh & Đồng bộ Báo cáo; Sinh & Đồng bộ Chứng thư; và **Tạo & Xem lại bộ tài liệu hồ sơ — Iteration 1**.

Không có S14, màn Kiểm tra hồ sơ riêng, KSCL/phê duyệt nhiều cấp, NCCQ aggregate trung gian hoặc màn Kiểm tra quy tắc đối chiếu giá.

## 1. North-star flow
```text
Trang chủ → Quản lý yêu cầu sơ bộ → Tạo yêu cầu sơ bộ → Upload & Mapping Excel
→ Phân tích danh mục → Rà soát tích hợp → Tạo file kết quả sơ bộ
→ Chuyển sang thẩm định chính thức → Tổng quan hồ sơ
→ Xác nhận & điều chỉnh danh mục → Workbench tài sản → Asset Context Drawer
→ Nguồn giá & Chứng cứ → Tạo & quản lý báo giá NCC
→ Hoàn tất từng báo giá NCC → Chọn NCC đã xác nhận giá
→ Kết quả thẩm định giá
→ Microsoft 365 Document Workspace
   → Tạo & Xem lại bộ tài liệu hồ sơ
      → Tạo hàng loạt từ mẫu có sẵn
      → Review từng tài liệu trong preview lớn
      → Đồng bộ dữ liệu khi hồ sơ thay đổi
      → Mẫu tùy biến của hồ sơ khi cần
   → Báo cáo / Chứng thư: child-flow Managed Regions/Generation-Sync chuyên sâu khi cần
   → Đồng bộ dữ liệu & Quản lý phiên bản
   → Phát hành bộ tài liệu
```

## 2. Price & Evidence
Ưu tiên: `Giá khảo sát Internet → Thuyết minh đơn giá → Giá Kết quả thẩm định giá hồ sơ cũ`. Giá NCC không phải nguồn chính xác định đơn giá cuối cùng. Giá NCC thấp hơn đơn giá hiện hành luôn Warning; chênh tuyệt đối >15% là Warning; Warning không Blocking.

## 3. Kết quả thẩm định giá
03 bảng biểu mẫu công ty immutable; không đổi tên/thứ tự cột, split/merge/cardize; giữ Tổng cộng, Làm tròn, số tiền bằng chữ.

## 4. Template / AI / Spreadsheet
AI chỉ phân tích/gợi ý/test; user xác nhận mapping/template. Không silent accept/publish/overwrite/change formula.

Bảng tính: `Hn = MIN(En:Gn)`; `In = Dn*Hn`. Fill Engine: `Chuẩn bị → Mapping → Preview & Validate → Fill & Recalculate → Save & Version`; không overwrite template/staticize formula/silent drop workbook feature.

## 5. Microsoft 365 Document Workspace
VALORA quản lý structured data, Data Snapshot, lineage, audit, sync status, release manifest. Microsoft 365 quản lý Word/file/file version. Document Revision != Microsoft 365 file version.

### 5.1 Tạo & Xem lại bộ tài liệu hồ sơ — Baseline Iteration 1
Các tài liệu có mẫu sẵn như Quyết định, Kế hoạch, Phiếu KSCL và các tài liệu cấu hình khác được **sinh hàng loạt**, không tạo workflow riêng cho từng loại.

Mental model:
```text
Bộ mẫu → Data Snapshot → Tạo hàng loạt → Xem lại → Đồng bộ khi dữ liệu thay đổi → Phát hành
```

Layout Fluent 2: summary cards phía trên; danh sách tài liệu bên trái; **preview tài liệu lớn ở trung tâm là vùng chính**; panel phải hiển thị metadata, Template Version, Document Revision, file Microsoft 365, mapping/Managed Regions và lịch sử đồng bộ. Có zoom, chuyển trang, full-screen, `Mở trong Word`. Preview view-only; không fake Word editor. Mockup trước có review nhỏ bị supersede.

Batch có thể dùng chung Data Snapshot nhưng từng tài liệu có lineage riêng:
```text
Template Version → Data Snapshot → Document Revision → Microsoft 365 file/version
```

Trạng thái workspace ưu tiên tái sử dụng `Sẵn sàng / Cần cập nhật / Chưa hoàn tất / Lỗi`. Managed Regions sau khi Word tồn tại tiếp tục dùng `Đã đồng bộ / Cần cập nhật / Bạn tự chỉnh trong Word / Lỗi`.

### 5.2 Đồng bộ khi thông tin hồ sơ thay đổi
VALORA phát hiện tài liệu/vùng đang dùng snapshot cũ. User nhấn **`Đồng bộ dữ liệu`** để xem khác biệt, chọn tài liệu/vùng rồi mới ghi. Không silent overwrite. Narrative ngoài Managed Regions giữ nguyên; conflict trong vùng phải xử lý trước. Revision/release đã phát hành immutable; cập nhật tạo revision mới.

### 5.3 Mẫu tùy biến của hồ sơ
Có CTA `Tải lên mẫu tùy biến`.
```text
Upload .docx → AI phân tích → đối chiếu dữ liệu hồ sơ → nhận diện/gợi ý trường → highlight vị trí → đề xuất mapping/Managed Regions → user xác nhận → test fill → lưu Template Version
```
AI không tự chốt mapping. Mẫu mới mặc định chỉ thuộc hồ sơ hiện tại. Chỉ khi user explicit `Lưu vào thư viện mẫu` mới trở thành mẫu tái sử dụng ngoài hồ sơ; không auto-promote tài liệu khách hàng thành global template.

### 5.4 Báo cáo & Chứng thư
Hai loại này giữ Generation/Sync + Managed Regions baselines riêng. Workspace bộ tài liệu là orchestration layer, không thay thế child-flow chuyên sâu.

### 5.5 Publishing
Tiếp tục authority: `Chọn tài liệu → Kiểm tra tình trạng → Xem bộ tài liệu → Xác nhận phát hành → Khóa phiên bản đã phát hành`. Không có `Xuất PDF` trong baseline.

## 6. Guardrails
- Single-user; AI advisory.
- Không fake Word/Excel editor.
- Không silent mapping/sync/overwrite/publish.
- Không auto-promote mẫu riêng của hồ sơ.
- Preview review-first, chiếm diện tích chính.
- Một primary CTA mỗi context.
- Workbench + database là nguồn dữ liệu nghiệp vụ chính thức.
- Published revision/release immutable.

## 7. Capability inventory
| Capability | Trạng thái |
|---|---|
| S09–S13 | P0 baseline |
| NCCQ | P0 baseline Iteration 6 |
| Result | P0 baseline; 03 bảng immutable |
| Microsoft 365 Document Workspace | P0 baseline |
| **Tạo & Xem lại bộ tài liệu hồ sơ** | **P0 baseline Iteration 1** |
| Managed Regions — Báo cáo | P0 baseline |
| Managed Regions — Chứng thư | P0 baseline |
| Sinh & Đồng bộ Báo cáo | P0 baseline |
| Sinh & Đồng bộ Chứng thư | P0 baseline |
| Sync/Version | P0 baseline |
| Publishing | P0 baseline |
| Spreadsheet Fill Engine | P0 baseline |

## 8. Companion authority
- `VALORA_UIUX_HANDOFF_v2.3_DOCUMENT_SET_BATCH_REVIEW_BASELINE_ADDENDUM.md`.
- Các addendum Generation/Sync, Managed Regions, Sync-Version, Publishing, Fill Engine, NCC warning, Template/AI, Result/NCCQ hiện hành tiếp tục có hiệu lực trong scope tương ứng.

## 9. ADR
Baseline này khóa UI/UX + domain interaction. Batch transaction semantics, template-scope persistence, AI-to-managed-region conversion, conflict detection hoặc multi-document sync semantics phải đánh giá ADR khi implementation làm thay đổi persistence/architecture.
