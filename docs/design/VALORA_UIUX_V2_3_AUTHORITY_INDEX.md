# VALORA UI/UX v2.3 — Authority Index

**Status:** Canonical UI/UX reading order for v2.3  
**Purpose:** Ngăn iteration/addendum cũ override các quyết định đã được consolidate hoặc authority mới hơn.

## 1. Thứ tự đọc hiện hành

1. `VALORA_UIUX_HANDOFF_v2.3.md` — canonical master đã consolidate tại thời điểm commit consolidation.
2. `VALORA_UIUX_HANDOFF_v2.3_TEMPLATE_MANAGEMENT_BASELINE_ADDENDUM.md` — **authority mới nhất cho Quản lý mẫu tài liệu generic — Iteration 1**; supersede IA hẹp coi template management chỉ thuộc `03_Hợp đồng`.
3. `VALORA_UIUX_HANDOFF_v2.3_GENERIC_DOCUMENT_MAPPING_BASELINE_ADDENDUM.md` — authority Mapping Template tài liệu generic — Iteration 2, UX Word generic thân thiện cho người nghiệp vụ.
4. `VALORA_UIUX_HANDOFF_v2.3_GENERIC_DOCUMENT_TEMPLATE_REVIEW_BASELINE_ADDENDUM.md` — authority Bước 3 Kiểm tra & hoàn tất template — Iteration 1.
5. `VALORA_UIUX_HANDOFF_v2.3_PRICE_EVIDENCE_AUTHORITY_ADDENDUM.md` — companion nguồn giá/chứng cứ.
6. `VALORA_UIUX_HANDOFF_v2.3_FINAL_RESULT_BASELINE_ADDENDUM.md` — companion Kết quả thẩm định giá.
7. `VALORA_UIUX_HANDOFF_v2.3_M365_DOCUMENT_WORKSPACE_BASELINE_ADDENDUM.md` — companion Microsoft 365 Document Workspace.
8. `VALORA_UIUX_HANDOFF_v2.3_S17_BASELINE_ADDENDUM.md` — companion lịch sử child flow Hoàn tất 01 báo giá NCC; không chèn whole-case readiness.
9. `VALORA_UIUX_HANDOFF_v2.3_TM04_BASELINE_ADDENDUM.md` — companion TM04 Preview/Test fill.
10. `VALORA_USER_FLOW_MINDMAP_v2.3.md` — flow map hỗ trợ đọc; không override authority nghiệp vụ.

Quyết định explicit mới hơn thắng trong đúng scope. Generic Template Management quản lý lifecycle/listing chung nhưng không override specialized mapping/fill authority của từng format/document type.

## 2. Price & Evidence authority

```text
1. Giá khảo sát từ Internet
2. Thuyết minh đơn giá
3. Giá trong phần Kết quả thẩm định giá của hồ sơ cũ
```

Giá NCC không phải nguồn chính xác định Đơn giá thẩm định cuối cùng; phục vụ tạo/tái tạo báo giá và đối chiếu.

```text
Đơn giá Kết quả định giá <= Đơn giá báo giá NCC dùng để đối chiếu
→ phù hợp theo rule nghiệp vụ/tiêu chuẩn đang áp dụng trong VALORA
```

## 3. Routing authority

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
```

Không có NCCQ aggregate hoặc S17 readiness toàn hồ sơ nằm giữa `Chọn nhà cung cấp đã xác nhận giá` và `Kết quả thẩm định giá`.

## 4. Baseline visual authority

- NCCQ — Iteration 6.
- TM01 — Iteration 1.
- TM03 — Iteration 1 Word-only.
- TM04 — Iteration 1.
- Hoàn tất 01 báo giá NCC — Iteration 3, scope 01 báo giá / 01 NCC.
- Kết quả thẩm định giá — Iteration 1.
- Microsoft 365 Document Workspace — baseline authority.
- Mapping Template tài liệu generic — Iteration 2.
- Kiểm tra & hoàn tất template — Iteration 1.
- **Quản lý mẫu tài liệu generic — Iteration 1.**

## 5. Template Management authority

IA authority:

```text
Cấu hình
→ Mẫu tài liệu
→ Quản lý mẫu tài liệu
```

Nhóm template tối thiểu:

```text
Tất cả
Hợp đồng & hồ sơ liên quan
Báo cáo thẩm định giá
Chứng thư thẩm định giá
Phụ lục / Bảng tính Excel
Báo giá nhà cung cấp
```

`03_Hợp đồng` chỉ là contextual entry/filter cho `Hợp đồng & hồ sơ liên quan`, không sở hữu toàn bộ hệ thống template.

Bảng quản lý ưu tiên table-first và hiển thị `Loại tài liệu | Tên mẫu | Định dạng | Phiên bản | Mặc định | Trạng thái | Cập nhật gần nhất | Người cập nhật | Thao tác`.

Word `.docx` và Excel `.xlsx/.xlsm` có thể cùng được quản lý metadata/lifecycle trong module generic. Tuy nhiên Báo giá NCC vẫn Word `.docx` only. Excel mapping/fill cần authority riêng; không áp Word region semantics máy móc cho Excel.

## 6. Generic Document Mapping authority

```text
Chọn mẫu Word
→ Chọn dữ liệu nghiệp vụ
→ Click vị trí cần điền trong Word
→ VALORA tạo mapping phía sau
→ Kiểm tra & hoàn tất
```

UI không bắt người dùng hiểu Region ID/field path/source collection. Cách cập nhật hiển thị bằng ngôn ngữ nghiệp vụ: `Tự cập nhật khi dữ liệu thay đổi`, `Chỉ điền lần đầu`, `Người dùng tự chỉnh trong Word`.

Bước 3 dùng preview Word đã fill bằng dữ liệu test; tổng hợp `Đã mapping`, `Chưa mapping`, `Cảnh báo`, `Không tìm thấy vùng`; validation Blocking/Warning/Info; chỉ `Template hợp lệ` khi không còn Blocking. Preview/test không tạo tài liệu nghiệp vụ chính thức.

## 7. Guardrail

- Design authority không đồng nghĩa product code đã implement.
- AI/Kho tri thức chỉ gợi ý; user quyết định nghiệp vụ chính thức.
- Workbench + database là nguồn dữ liệu nghiệp vụ chính thức.
- Mỗi thay đổi giá có history/lineage/audit.
- STT tài sản bất biến.
- 03 bảng Kết quả thẩm định giá là immutable layout.
- Template báo giá NCC chỉ Word `.docx`.
- Document Workspace không có `Xuất PDF` trong baseline.
- File generated và signed scan là hai artifact khác nhau, có lineage.
- Template/version đã dùng không silent overwrite.
- Generic management không override specialized authority của Word NCC, Word generic hoặc Excel tương lai.
- Không đưa dữ liệu thật vào public repository.
