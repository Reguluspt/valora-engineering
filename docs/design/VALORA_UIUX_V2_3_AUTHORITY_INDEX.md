# VALORA UI/UX v2.3 — Authority Index

**Status:** Canonical UI/UX reading order for v2.3  
**Purpose:** Ngăn iteration/addendum cũ override các quyết định đã được consolidate hoặc authority mới hơn.  
**Consolidation:** v2.3 lần 2 — 31/08/2026; cập nhật authority Fill Engine + NCC price warning ngày 31/08/2026.

## 1. Thứ tự đọc hiện hành

1. `VALORA_UIUX_HANDOFF_v2.3.md` — canonical master; điểm đọc chính sau consolidation.
2. `VALORA_UIUX_HANDOFF_v2.3_SPREADSHEET_FILL_ENGINE_BASELINE_ADDENDUM.md` — **Baseline / Design Authority `Bảng tính Fill Engine — Implementation Contract v1 — Iteration 1`**.
3. `VALORA_UIUX_HANDOFF_v2.3_NCC_PRICE_WARNING_RULE_ADDENDUM.md` — **Current Business Rule Authority** cho cảnh báo `Giá NCC ↔ Đơn giá hiện hành` ngay tại NCCQ; supersede màn `Kiểm tra quy tắc đối chiếu giá` đã bị bỏ.
4. `VALORA_UIUX_HANDOFF_v2.3_MANAGED_REGIONS_CERTIFICATE_BASELINE_ADDENDUM.md` — **Baseline / Design Authority `Managed Regions — Chứng thư thẩm định giá — Iteration 1`**.
5. `VALORA_UIUX_HANDOFF_v2.3_DOCUMENT_PUBLISH_BASELINE_ADDENDUM.md` — **Baseline / Design Authority `Phát hành bộ tài liệu — Iteration 1`**.
6. `VALORA_UIUX_HANDOFF_v2.3_DOCUMENT_SYNC_VERSION_BASELINE_ADDENDUM.md` — **Baseline / Design Authority `Đồng bộ dữ liệu & Quản lý phiên bản tài liệu — Iteration 1`**.
7. `VALORA_UIUX_HANDOFF_v2.3_MANAGED_REGIONS_REPORT_BASELINE_ADDENDUM.md` — **Baseline / Design Authority `Managed Regions — Báo cáo thẩm định giá — Iteration 1`**.
8. `VALORA_UIUX_HANDOFF_v2.3_CONTRACT_DOCUMENT_WORKSPACE_BASELINE_ADDENDUM.md` — Baseline `03_Hợp đồng — Danh sách & tạo tài liệu — Iteration 1`.
9. `VALORA_UIUX_HANDOFF_v2.3_AI_TEMPLATE_FINAL_CHECK_BASELINE_ADDENDUM.md` — Baseline Bước 4: Kiểm tra & hoàn tất — Iteration 1, Word + Bảng tính.
10. `VALORA_UIUX_HANDOFF_v2.3_AI_TEMPLATE_ASSISTANT_BASELINE_ADDENDUM.md` — companion AI Template Assistant.
11. `VALORA_UIUX_HANDOFF_v2.3_AI_TEMPLATE_REVIEW_EDIT_BASELINE_ADDENDUM.md` — companion Bước 3.
12. `VALORA_UIUX_HANDOFF_v2.3_TEMPLATE_MANAGEMENT_BASELINE_ADDENDUM.md` — companion Quản lý mẫu tài liệu generic.
13. `VALORA_UIUX_HANDOFF_v2.3_GENERIC_DOCUMENT_MAPPING_BASELINE_ADDENDUM.md` — companion Word generic Mapping.
14. `VALORA_UIUX_HANDOFF_v2.3_GENERIC_DOCUMENT_TEMPLATE_REVIEW_BASELINE_ADDENDUM.md` — companion Word generic Review.
15. `VALORA_UIUX_HANDOFF_v2.3_PRICE_EVIDENCE_AUTHORITY_ADDENDUM.md` — companion Price & Evidence.
16. `VALORA_UIUX_HANDOFF_v2.3_FINAL_RESULT_BASELINE_ADDENDUM.md` — companion Kết quả thẩm định giá.
17. `VALORA_UIUX_HANDOFF_v2.3_M365_DOCUMENT_WORKSPACE_BASELINE_ADDENDUM.md` — companion Microsoft 365 Document Workspace.
18. `VALORA_UIUX_HANDOFF_v2.3_S17_BASELINE_ADDENDUM.md` — companion child flow Hoàn tất 01 báo giá NCC.
19. `VALORA_UIUX_HANDOFF_v2.3_TM04_BASELINE_ADDENDUM.md` — companion TM04.
20. `VALORA_USER_FLOW_MINDMAP_v2.3.md` — flow map hỗ trợ đọc; không override master.

Master là điểm đọc chính sau consolidation. Quyết định explicit mới hơn master thắng trong đúng scope cho tới lần consolidation tiếp theo.

## 2. Routing authority

```text
Trang chủ
→ Quản lý yêu cầu sơ bộ
→ Tạo yêu cầu sơ bộ
→ Upload & Mapping Excel
→ Phân tích danh mục
→ Rà soát tích hợp
→ Tạo file kết quả sơ bộ
→ Chuyển sang thẩm định chính thức
→ Tổng quan hồ sơ
→ Xác nhận & điều chỉnh danh mục triển khai
→ Workbench tài sản / Asset Context Drawer
→ Nguồn giá & Chứng cứ
→ Tạo & quản lý báo giá NCC
→ Hoàn tất từng báo giá NCC
→ Chọn nhà cung cấp đã xác nhận giá
→ Kết quả thẩm định giá
→ Microsoft 365 Document Workspace / Bộ tài liệu phát hành
   → 03_Hợp đồng — Danh sách & tạo tài liệu
   → Báo cáo thẩm định giá — Quản lý vùng dữ liệu / Managed Regions
   → Chứng thư thẩm định giá — Quản lý nội dung do VALORA quản lý / Managed Regions
      → Đồng bộ dữ liệu & Quản lý phiên bản tài liệu
   → Phát hành bộ tài liệu
```

Supporting configuration flow:

```text
Cấu hình → Mẫu tài liệu → Quản lý mẫu tài liệu
→ Chọn/Tạo mẫu → AI phân tích & đề xuất
→ Rà soát & chỉnh sửa → Kiểm tra & hoàn tất
→ Bảng tính Fill Engine: Chuẩn bị → Mapping → Preview & Validate → Fill & Recalculate → Save & Version
```

## 3. Price & Evidence authority

```text
1. Giá khảo sát từ Internet
2. Thuyết minh đơn giá
3. Giá trong phần Kết quả thẩm định giá của hồ sơ cũ
```

Giá NCC không phải nguồn chính xác định Đơn giá thẩm định cuối cùng; phục vụ tạo/tái tạo báo giá, evidence/lineage và đối chiếu.

```text
Đơn giá Kết quả định giá <= Đơn giá báo giá NCC dùng để đối chiếu
→ phù hợp theo rule nghiệp vụ/tiêu chuẩn đang áp dụng trong VALORA
```

Cách xác định tập báo giá bắt buộc để đối chiếu chưa được user khóa thành công thức min/max/every-quote; không tự suy diễn.

### 3.1 Cảnh báo giá NCC — authority mới nhất

Không có màn `Kiểm tra quy tắc đối chiếu giá` riêng. Cảnh báo hiển thị ngay tại `Tạo & quản lý báo giá NCC` theo từng dòng:

```text
Giá NCC < Đơn giá hiện hành
→ luôn Warning

|Giá NCC - Đơn giá hiện hành| / Đơn giá hiện hành > 15%
→ Warning chênh lệch lớn
```

Suy ra phía cao: `Giá NCC > 115% × Đơn giá hiện hành → Warning`. Warning không Blocking; VALORA không tự sửa Giá NCC, không tự sửa Đơn giá hiện hành và không tự chọn giá thay user.

UI nên truy cập được ngay tại dòng: `Đơn giá hiện hành | Giá NCC | Chênh tiền | Chênh % | Cảnh báo`.

## 4. Baseline visual authority

- NCCQ — Iteration 6.
- TM01 — Iteration 1.
- TM03 — Iteration 1 Word-only.
- TM04 — Iteration 1.
- Hoàn tất 01 báo giá NCC — Iteration 3.
- Kết quả thẩm định giá — Iteration 1.
- Microsoft 365 Document Workspace — baseline authority.
- `03_Hợp đồng — Danh sách & tạo tài liệu` — Baseline Iteration 1.
- `Managed Regions — Báo cáo thẩm định giá` — Baseline Iteration 1.
- **`Managed Regions — Chứng thư thẩm định giá` — Baseline Iteration 1.**
- `Đồng bộ dữ liệu & Quản lý phiên bản tài liệu` — Baseline Iteration 1.
- `Phát hành bộ tài liệu` — Baseline Iteration 1.
- Mapping Template tài liệu generic Word — Iteration 2.
- Kiểm tra & hoàn tất template Word generic — Iteration 1.
- Quản lý mẫu tài liệu generic — Iteration 1.
- Thiết lập mẫu tài liệu — AI phân tích & đề xuất — Iteration 1.
- Thiết lập mẫu tài liệu — Bước 3 — Iteration 1.
- Thiết lập mẫu tài liệu — Bước 4 Word + Bảng tính — Baseline Iteration 1.
- **Bảng tính Fill Engine — Implementation Contract v1 — Baseline Iteration 1; Fluent 2 desktop-first.**

## 5. Document Workspace authority

Managed Regions user-facing titles ưu tiên:

- Báo cáo: `Quản lý vùng dữ liệu trong Báo cáo thẩm định giá`.
- Chứng thư: `Quản lý nội dung do VALORA quản lý (Chứng thư thẩm định giá)`.

Hai loại tài liệu dùng chung mental model:

```text
1. Xem nội dung VALORA quản lý
→ 2. Xem khác biệt
→ 3. Chọn nội dung cần cập nhật
→ 4. Đồng bộ vào Word
```

Trạng thái vùng: `Đã đồng bộ / Cần cập nhật / Bạn tự chỉnh trong Word / Lỗi`. Comparison: `Dữ liệu từ VALORA ↔ Nội dung đang có trong Word`. Chỉ vùng user chọn mới được ghi; narrative ngoài vùng giữ nguyên; conflict trong managed region phải được xem/xử lý trước khi ghi.

Các nhóm nội dung minh họa trên mockup Chứng thư không phải danh sách field hard-code; vùng thực tế đến từ Template Version + mapping.

Sync/version flow:

```text
1. Xem những gì đã thay đổi
→ 2. Xem chi tiết khác biệt
→ 3. Chọn nội dung muốn cập nhật
→ 4. Cập nhật vào Word & tạo/ghi nhận phiên bản
```

Publishing flow:

```text
1. Chọn tài liệu
→ 2. Kiểm tra tình trạng
→ 3. Xem bộ tài liệu
→ 4. Xác nhận phát hành
→ Khóa phiên bản đã phát hành
```

Publish status user-facing: `Sẵn sàng / Cần cập nhật / Chưa hoàn tất / Không áp dụng / Đã phát hành`.

Chỉ tài liệu đủ điều kiện theo loại tài liệu mới được chọn. Package có Blocking thì primary publish CTA không khả dụng. Không tạo màn Kiểm tra hồ sơ hay KSCL/phê duyệt nhiều cấp mới.

Khi phát hành, freeze release manifest: tập artifact đã chọn + Document Revision + Data Snapshot nếu có + Microsoft 365 file/version + thời điểm + người thao tác. Release cũ không silent mutate; sửa sau phát hành phải tạo revision/version mới và package phát hành mới.

Document Revision và Microsoft 365 file version là hai lớp lineage liên kết nhưng không đồng nhất.

## 6. Template Management / AI authority

IA: `Cấu hình → Mẫu tài liệu → Quản lý mẫu tài liệu`. Nhóm tối thiểu: Tất cả; Hợp đồng & hồ sơ liên quan; Báo cáo thẩm định giá; Chứng thư thẩm định giá; Bảng tính; Báo giá nhà cung cấp.

AI-assisted flow: `Chọn mẫu → AI phân tích & đề xuất → Rà soát & chỉnh sửa → Kiểm tra & hoàn tất`. AI chỉ đề xuất/phân tích/test; user xác nhận mapping/template chính thức.

## 7. 03_Hợp đồng authority

`03_Hợp đồng` quản lý working documents do VALORA sinh/tạo trong vòng đời hợp đồng. Bảng baseline:

```text
STT | Tên tài liệu | Loại tài liệu | Số / Ký hiệu |
Trạng thái | Phiên bản | Cập nhật lần cuối | Tác vụ
```

Primary CTA: `Tạo tài liệu`. Lifecycle artifact: `Bản nháp → Cần đồng bộ → Đã đồng bộ → Sẵn sàng phát hành → Đã phát hành`. VALORA không xây Word editor giả; signed scan thuộc `05_Pháp lý`.

## 8. Bảng tính authority

Reference `Bang Tinh - HĐ 42.xlsx` khóa:

```text
Hn = MIN(En:Gn)
In = Dn*Hn
```

AI/engine không tự thay formula. Validation kiểm tra formula/relative reference, tổng/làm tròn, merge/style/border/number format, evidence/image, print/page layout và workbook feature có nguy cơ không được bảo toàn.

### 8.1 Fill Engine baseline

Mental flow:

```text
Chuẩn bị → Mapping → Preview & Validate → Fill & Recalculate → Save & Version
```

Logical contract:

```text
Data Sources → Mapping Engine → Fill Engine Core → Excel Processor → Validator → Output & Lineage
```

Safety: không ghi đè file mẫu; luôn tạo output mới; chỉ ghi vùng mapping được phép; giữ formula/cấu trúc/định dạng; có Fill Manifest + audit; không silent drop workbook feature. Repeating rows phải giữ relative references. Validator dùng `Blocking / Warning / Info` và không tạo checkpoint kiểm tra hồ sơ riêng.

Lineage tối thiểu: `Template Version → Fill Run / Manifest → Output File → Lineage & Audit`.

## 9. Guardrail

- Design authority không đồng nghĩa product code đã implement.
- AI chỉ gợi ý; user quyết định nghiệp vụ/mapping chính thức.
- AI không silent publish/accept/overwrite.
- Workbench + database là nguồn dữ liệu nghiệp vụ chính thức.
- Giá/chứng cứ không silent overwrite Đơn giá hiện hành.
- Cảnh báo giá NCC là Warning tại NCCQ, không Blocking và không tạo checkpoint riêng.
- 03 bảng Kết quả thẩm định giá là immutable layout.
- Template báo giá NCC chỉ Word `.docx`.
- Document Workspace không có `Xuất PDF` trong baseline.
- Generated file và signed scan là hai artifact khác nhau, có lineage.
- Managed Regions Báo cáo/Chứng thư không silent sync và không overwrite narrative ngoài vùng.
- Sync/version không silent mutate revision đã phát hành.
- Publishing không silent publish/lock/mutate release; không tự thêm hoặc âm thầm bỏ tài liệu khỏi package.
- Fill Engine không overwrite template, không staticize formula và không silent drop workbook feature.
- Không đưa dữ liệu thật vào public repository.
