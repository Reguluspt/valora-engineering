# VALORA UI/UX v2.3 — Authority Index

**Status:** Canonical UI/UX reading order for v2.3  
**Purpose:** Ngăn iteration/addendum cũ override các quyết định đã được consolidate hoặc authority mới hơn.

## 1. Thứ tự đọc hiện hành

1. `VALORA_UIUX_HANDOFF_v2.3.md` — canonical master đã consolidate tại thời điểm commit consolidation.
2. `VALORA_UIUX_HANDOFF_v2.3_AI_TEMPLATE_ASSISTANT_BASELINE_ADDENDUM.md` — authority Thiết lập mẫu tài liệu AI-assisted, flow 4 bước cho Word generic và Bảng tính.
3. `VALORA_UIUX_HANDOFF_v2.3_AI_TEMPLATE_REVIEW_EDIT_BASELINE_ADDENDUM.md` — **authority mới nhất cho Bước 3: Rà soát & chỉnh sửa — Iteration 1**; user review/edit, bổ sung field AI bỏ sót, formula/data-region semantics.
4. `VALORA_UIUX_HANDOFF_v2.3_TEMPLATE_MANAGEMENT_BASELINE_ADDENDUM.md` — authority Quản lý mẫu tài liệu generic — Iteration 1.
5. `VALORA_UIUX_HANDOFF_v2.3_GENERIC_DOCUMENT_MAPPING_BASELINE_ADDENDUM.md` — authority Word generic mapping Iteration 2; được AI-assisted flow bổ sung nhưng giữ specialized Word guardrails.
6. `VALORA_UIUX_HANDOFF_v2.3_GENERIC_DOCUMENT_TEMPLATE_REVIEW_BASELINE_ADDENDUM.md` — authority Kiểm tra & hoàn tất template Word — Iteration 1.
7. `VALORA_UIUX_HANDOFF_v2.3_PRICE_EVIDENCE_AUTHORITY_ADDENDUM.md` — companion nguồn giá/chứng cứ.
8. `VALORA_UIUX_HANDOFF_v2.3_FINAL_RESULT_BASELINE_ADDENDUM.md` — companion Kết quả thẩm định giá.
9. `VALORA_UIUX_HANDOFF_v2.3_M365_DOCUMENT_WORKSPACE_BASELINE_ADDENDUM.md` — companion Microsoft 365 Document Workspace.
10. `VALORA_UIUX_HANDOFF_v2.3_S17_BASELINE_ADDENDUM.md` — companion child flow Hoàn tất 01 báo giá NCC.
11. `VALORA_UIUX_HANDOFF_v2.3_TM04_BASELINE_ADDENDUM.md` — companion TM04 Preview/Test fill.
12. `VALORA_USER_FLOW_MINDMAP_v2.3.md` — flow map hỗ trợ đọc; không override authority nghiệp vụ.

Quyết định explicit mới hơn thắng trong đúng scope. AI-assisted authorities không override specialized authority của template Báo giá NCC hoặc immutable company forms.

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
- Quản lý mẫu tài liệu generic — Iteration 1.
- Thiết lập mẫu tài liệu — AI phân tích & đề xuất — Iteration 1.
- **Thiết lập mẫu tài liệu — Bước 3: Rà soát & chỉnh sửa — Iteration 1.**

## 5. Template Management authority

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

`Bảng tính` là terminology nghiệp vụ chính thức cho nhóm Excel. `03_Hợp đồng` chỉ là contextual entry/filter cho nhóm hợp đồng.

Word `.docx` và Bảng tính `.xlsx/.xlsm` có thể cùng được quản lý metadata/lifecycle. Báo giá NCC vẫn Word `.docx` only.

## 6. AI Template Assistant authority

Flow:

```text
1. Chọn mẫu
→ 2. AI phân tích & đề xuất
→ 3. Rà soát & chỉnh sửa
→ 4. Kiểm tra & hoàn tất
```

AI có thể phân tích, đề xuất mapping, giải thích, highlight, test, phát hiện lỗi/vùng chưa thiết lập và đề xuất sửa. AI không tự publish, silent accept hoặc overwrite Template Version đang dùng.

Confidence dùng `Tin cậy cao | Cần xác nhận | Chưa xác định`.

## 7. Bước 3 — Rà soát & chỉnh sửa authority

Bước 3 là checkpoint user-controlled cho mapping.

Trạng thái tối thiểu:

```text
Đã mapping
Cần xác nhận
Chưa mapping
Đã bỏ qua
```

Preview là vùng lớn nhất; mapping panel bên phải có summary, search/filter, grouping và focus/highlight vị trí. Selected-region inspector cho phép `Giữ nguyên/Xác nhận | Đổi gán dữ liệu | Không dùng vùng này`.

Capability `Bổ sung trường AI bỏ sót` là bắt buộc. User có thể chọn vị trí trước hoặc chọn dữ liệu trước rồi gán. Nếu không có field phù hợp, có thể tạo custom field theo guardrail; custom field không tự trở thành canonical domain field.

`Đã bỏ qua` phải là explicit user intent, không do AI silent skip.

Bước 3 có `Quay lại Bước 2 | Lưu nháp | Tiếp tục: Kiểm tra & hoàn tất`; navigation không làm mất thay đổi mapping.

## 8. Bảng tính authority

Bảng tính dùng analyzer/fill semantics riêng, không áp Word region semantics máy móc. AI có thể nhận diện workbook/sheet, vùng/cột/dòng mẫu, section/group, merge, formula, tổng hợp, style, ảnh/chứng cứ và print/page layout.

Mapping ưu tiên vùng/cột/dòng mẫu thay vì bắt user map từng cell.

Với case `Bang Tinh - HĐ 42.xlsx`:

```text
Hn = MIN(En:Gn)
In = Dn*Hn
```

Formula region phải hiển thị là `Giữ công thức từ mẫu`, không được biến thành static data mapping. `MIN(E:G)` là template formula authority và không được AI tự đổi.

Nguồn khảo sát có thể chứa URL, text, hồ sơ nguồn và ảnh/chứng cứ.

## 9. Word mapping authority

Word generic giữ mental model thân thiện; không bắt user hiểu Region ID/field path/source collection. Bước 3 cho phép user click đoạn/vị trí/table/repeating row để xác nhận/sửa/bổ sung mapping và chọn `Người dùng tự chỉnh trong Word` khi phù hợp.

## 10. Bước 4 boundary

Bước 3 tập trung mapping correctness và user intent. Bước 4 tập trung test fill, validation và khả năng hoàn tất template.

Bước cuối phải rà vùng chưa thiết lập với `Gán dữ liệu | Bỏ qua có chủ đích | Đây là nội dung cố định`, severity `Blocking | Warning | Info`; không còn Blocking mới được coi template hợp lệ.

## 11. Guardrail

- Design authority không đồng nghĩa product code đã implement.
- AI chỉ đề xuất; user quyết định mapping chính thức.
- User luôn có quyền bổ sung field AI bỏ sót và sửa/xóa mapping AI.
- `Đã bỏ qua` cần explicit user intent.
- AI Template Assistant không tự publish/silent accept/silent overwrite.
- Formula template không biến thành static mapping.
- AI không tự đổi `MIN(E:G)`.
- Workbench + database là nguồn dữ liệu nghiệp vụ chính thức.
- Mỗi thay đổi giá có history/lineage/audit.
- STT tài sản bất biến trong business dataset; template-specific display behavior cần explicit mapping/authority.
- 03 bảng Kết quả thẩm định giá là immutable layout.
- Template báo giá NCC chỉ Word `.docx`.
- Document Workspace không có `Xuất PDF` trong baseline.
- File generated và signed scan là hai artifact khác nhau, có lineage.
- Template/version đã dùng không silent overwrite.
- Không đưa dữ liệu thật vào public repository.
