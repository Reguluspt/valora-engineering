# VALORA UI/UX v2.3 — Authority Index

**Status:** Canonical UI/UX reading order for v2.3  
**Purpose:** Ngăn iteration/addendum cũ override các quyết định đã được consolidate hoặc authority mới hơn.  
**Consolidation:** v2.3 lần 2 — 30/08/2026.

## 1. Thứ tự đọc hiện hành

1. `VALORA_UIUX_HANDOFF_v2.3.md` — **canonical master sau Consolidation v2.3 lần 2**; đã hợp nhất Price/Evidence, Final Result, M365 Workspace, Generic Template Management, Generic Word Mapping/Review, AI Template Assistant và Bảng tính authority hiện hành.
2. `VALORA_UIUX_HANDOFF_v2.3_AI_TEMPLATE_FINAL_CHECK_BASELINE_ADDENDUM.md` — **Baseline / Design Authority Bước 4: Kiểm tra & hoàn tất — Iteration 1**, dùng chung Word + Bảng tính với validation chuyên biệt theo format.
3. `VALORA_UIUX_HANDOFF_v2.3_AI_TEMPLATE_ASSISTANT_BASELINE_ADDENDUM.md` — companion visual/domain authority cho flow Thiết lập mẫu tài liệu 4 bước, Word generic + Bảng tính.
4. `VALORA_UIUX_HANDOFF_v2.3_AI_TEMPLATE_REVIEW_EDIT_BASELINE_ADDENDUM.md` — companion authority cho Bước 3: Rà soát & chỉnh sửa — Iteration 1.
5. `VALORA_UIUX_HANDOFF_v2.3_TEMPLATE_MANAGEMENT_BASELINE_ADDENDUM.md` — companion authority Quản lý mẫu tài liệu generic — Iteration 1.
6. `VALORA_UIUX_HANDOFF_v2.3_GENERIC_DOCUMENT_MAPPING_BASELINE_ADDENDUM.md` — companion authority Word generic Mapping — Iteration 2.
7. `VALORA_UIUX_HANDOFF_v2.3_GENERIC_DOCUMENT_TEMPLATE_REVIEW_BASELINE_ADDENDUM.md` — companion authority Word generic Kiểm tra & hoàn tất — Iteration 1.
8. `VALORA_UIUX_HANDOFF_v2.3_PRICE_EVIDENCE_AUTHORITY_ADDENDUM.md` — companion Price & Evidence.
9. `VALORA_UIUX_HANDOFF_v2.3_FINAL_RESULT_BASELINE_ADDENDUM.md` — companion Kết quả thẩm định giá.
10. `VALORA_UIUX_HANDOFF_v2.3_M365_DOCUMENT_WORKSPACE_BASELINE_ADDENDUM.md` — companion Microsoft 365 Document Workspace.
11. `VALORA_UIUX_HANDOFF_v2.3_S17_BASELINE_ADDENDUM.md` — companion child flow Hoàn tất 01 báo giá NCC.
12. `VALORA_UIUX_HANDOFF_v2.3_TM04_BASELINE_ADDENDUM.md` — companion TM04 Preview/Test fill NCC.
13. `VALORA_USER_FLOW_MINDMAP_v2.3.md` — flow map hỗ trợ đọc; không override master.

Từ commit Consolidation lần 2, master ở mục 1 là điểm đọc chính. Addendum dùng để truy vết chi tiết, visual baseline và nguồn quyết định. Quyết định explicit mới hơn master trong tương lai vẫn thắng trong đúng scope cho tới lần consolidation tiếp theo.

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
```

Supporting configuration flow:

```text
Cấu hình
→ Mẫu tài liệu
→ Quản lý mẫu tài liệu
→ Chọn/Tạo mẫu
→ AI phân tích & đề xuất
→ Rà soát & chỉnh sửa
→ Kiểm tra & hoàn tất
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

## 4. Baseline visual authority

- NCCQ — Iteration 6.
- TM01 — Iteration 1.
- TM03 — Iteration 1 Word-only.
- TM04 — Iteration 1.
- Hoàn tất 01 báo giá NCC — Iteration 3, scope 01 báo giá / 01 NCC.
- Kết quả thẩm định giá — Iteration 1.
- Microsoft 365 Document Workspace — baseline authority.
- Mapping Template tài liệu generic Word — Iteration 2.
- Kiểm tra & hoàn tất template Word generic — Iteration 1.
- Quản lý mẫu tài liệu generic — Iteration 1.
- Thiết lập mẫu tài liệu — AI phân tích & đề xuất — Iteration 1.
- Thiết lập mẫu tài liệu — Bước 3: Rà soát & chỉnh sửa — Iteration 1.
- **Thiết lập mẫu tài liệu — Bước 4: Kiểm tra & hoàn tất Word + Bảng tính — Baseline Iteration 1.**

Bước 4 dùng chung shell/mental model `Blocking / Warning / Info`; preview là vùng chính; validator/fill semantics chuyên biệt theo Word và Bảng tính. Template chỉ `Hợp lệ` khi không còn Blocking và không có silent publish.

## 5. Template Management / AI authority

IA:

```text
Cấu hình
→ Mẫu tài liệu
→ Quản lý mẫu tài liệu
```

Nhóm tối thiểu:

```text
Tất cả
Hợp đồng & hồ sơ liên quan
Báo cáo thẩm định giá
Chứng thư thẩm định giá
Bảng tính
Báo giá nhà cung cấp
```

`Bảng tính` là terminology nghiệp vụ chính thức cho nhóm Excel; không dùng `Phụ lục Excel` làm domain term chính.

AI-assisted flow:

```text
1. Chọn mẫu
→ 2. AI phân tích & đề xuất
→ 3. Rà soát & chỉnh sửa
→ 4. Kiểm tra & hoàn tất
```

AI chỉ đề xuất/phân tích/test; user xác nhận mapping/template chính thức.

Bước 3 dùng trạng thái:

```text
Đã mapping
Cần xác nhận
Chưa mapping
Đã bỏ qua
```

Capability `Bổ sung trường AI bỏ sót` là bắt buộc. `Đã bỏ qua` cần explicit user intent.

Bước 4 dùng severity:

```text
Blocking
Warning
Info
```

Vùng chưa thiết lập phải có `Gán dữ liệu`, `Bỏ qua có chủ đích`, `Đây là nội dung cố định`. Chỉ hoàn tất hợp lệ khi Blocking = 0; không silent publish.

## 6. Bảng tính authority

Bảng tính dùng analyzer/fill semantics riêng, không áp Word region semantics máy móc. Mapping ưu tiên vùng/cột/dòng mẫu thay vì map từng cell lặp.

Reference case `Bang Tinh - HĐ 42.xlsx` khóa template formula:

```text
Hn = MIN(En:Gn)
In = Dn*Hn
```

`MIN(E:G)` phải được giữ từ mẫu, không biến thành static mapping và không được AI/engine tự thay bằng business rule khác.

Nguồn khảo sát có thể chứa URL, text, hồ sơ nguồn và ảnh/chứng cứ.

Bước 4 phải kiểm tra formula/relative reference, tổng/làm tròn, merge/style/border/number format, evidence/image, print/page layout và các workbook feature có nguy cơ không được bảo toàn; lỗi bảo toàn phải được báo trước khi hoàn tất.

## 7. Guardrail

- Design authority không đồng nghĩa product code đã implement.
- AI chỉ gợi ý; user quyết định nghiệp vụ/mapping chính thức.
- AI không silent publish/accept/overwrite.
- User luôn có quyền bổ sung field AI bỏ sót và sửa/xóa mapping AI.
- Formula template không biến thành static mapping.
- AI không tự đổi `MIN(E:G)`.
- Workbench + database là nguồn dữ liệu nghiệp vụ chính thức.
- Mỗi thay đổi giá có history/lineage/audit.
- STT bất biến trong business dataset; template-specific display behavior cần explicit authority.
- 03 bảng Kết quả thẩm định giá là immutable layout.
- Template báo giá NCC chỉ Word `.docx`.
- Document Workspace không có `Xuất PDF` trong baseline.
- File generated và signed scan là hai artifact khác nhau, có lineage.
- Template/version đã dùng không silent overwrite.
- Không đưa dữ liệu thật vào public repository.
