# VALORA UI/UX v2.3 — Authority Index

**Status:** Canonical UI/UX reading order for v2.3  
**Purpose:** Ngăn iteration/addendum cũ override các quyết định đã được consolidate hoặc authority mới hơn.

## 1. Thứ tự đọc hiện hành

1. `VALORA_UIUX_HANDOFF_v2.3.md` — canonical master đã consolidate tại thời điểm commit consolidation.
2. `VALORA_UIUX_HANDOFF_v2.3_AI_TEMPLATE_ASSISTANT_BASELINE_ADDENDUM.md` — **authority mới nhất cho Thiết lập mẫu tài liệu — AI phân tích & đề xuất — Iteration 1**, áp dụng Word generic và Bảng tính; bổ sung AI-assisted pre-analysis, user review/recovery và Excel/Bảng tính semantics.
3. `VALORA_UIUX_HANDOFF_v2.3_TEMPLATE_MANAGEMENT_BASELINE_ADDENDUM.md` — authority Quản lý mẫu tài liệu generic — Iteration 1; module quản lý template cấp hệ thống.
4. `VALORA_UIUX_HANDOFF_v2.3_GENERIC_DOCUMENT_MAPPING_BASELINE_ADDENDUM.md` — authority Mapping Template tài liệu generic — Iteration 2 cho Word; được AI Template Assistant bổ sung pre-analysis nhưng không bị thay thế các guardrail Word mapping.
5. `VALORA_UIUX_HANDOFF_v2.3_GENERIC_DOCUMENT_TEMPLATE_REVIEW_BASELINE_ADDENDUM.md` — authority Kiểm tra & hoàn tất template Word — Iteration 1; validation dùng chung mental model Blocking/Warning/Info.
6. `VALORA_UIUX_HANDOFF_v2.3_PRICE_EVIDENCE_AUTHORITY_ADDENDUM.md` — companion nguồn giá/chứng cứ.
7. `VALORA_UIUX_HANDOFF_v2.3_FINAL_RESULT_BASELINE_ADDENDUM.md` — companion Kết quả thẩm định giá.
8. `VALORA_UIUX_HANDOFF_v2.3_M365_DOCUMENT_WORKSPACE_BASELINE_ADDENDUM.md` — companion Microsoft 365 Document Workspace.
9. `VALORA_UIUX_HANDOFF_v2.3_S17_BASELINE_ADDENDUM.md` — companion child flow Hoàn tất 01 báo giá NCC.
10. `VALORA_UIUX_HANDOFF_v2.3_TM04_BASELINE_ADDENDUM.md` — companion TM04 Preview/Test fill.
11. `VALORA_USER_FLOW_MINDMAP_v2.3.md` — flow map hỗ trợ đọc; không override authority nghiệp vụ.

Quyết định explicit mới hơn thắng trong đúng scope. AI Template Assistant bổ sung AI-assisted setup nhưng không override specialized authority của template Báo giá NCC hoặc immutable company forms.

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
- **Thiết lập mẫu tài liệu — AI phân tích & đề xuất — Iteration 1.**

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
Bảng tính
Báo giá nhà cung cấp
```

`Bảng tính` là terminology nghiệp vụ chính thức cho nhóm Excel; không dùng `Phụ lục Excel` làm domain term chính.

`03_Hợp đồng` chỉ là contextual entry/filter cho `Hợp đồng & hồ sơ liên quan`, không sở hữu toàn bộ hệ thống template.

Word `.docx` và Bảng tính `.xlsx/.xlsm` có thể cùng được quản lý metadata/lifecycle trong module generic. Báo giá NCC vẫn Word `.docx` only.

## 6. AI Template Assistant authority

Flow:

```text
1. Chọn mẫu
→ 2. AI phân tích & đề xuất
→ 3. Rà soát & chỉnh sửa
→ 4. Kiểm tra & hoàn tất
```

AI có thể phân tích, đề xuất mapping, giải thích, highlight, test, phát hiện lỗi/vùng chưa thiết lập và đề xuất sửa. AI không tự publish, không silent accept mapping và không overwrite Template Version đang dùng.

Confidence hiển thị bằng ngôn ngữ nghiệp vụ:

```text
Tin cậy cao
Cần xác nhận
Chưa xác định
```

Người dùng luôn có quyền `+ Thêm dữ liệu cần điền`, gán thủ công trường AI bỏ sót, sửa/xóa mapping AI, hoặc đánh dấu vùng là nội dung cố định/user-owned.

Nếu Data Model chưa có field phù hợp, có thể tạo `Trường tùy chỉnh của template`; không silently promote thành canonical business field.

Bước cuối phải rà lại vùng chưa thiết lập với action `Gán dữ liệu | Bỏ qua có chủ đích | Đây là nội dung cố định` và validation `Blocking | Warning | Info`.

## 7. Bảng tính authority

Bảng tính dùng analyzer/fill semantics riêng, không áp Word region semantics máy móc.

AI có thể nhận diện workbook/sheet, vùng/cột/dòng mẫu, section/group, merge, formula, tổng hợp, style, ảnh/chứng cứ và print/page layout.

Mapping ưu tiên vùng/cột/dòng mẫu thay vì bắt user map từng cell.

Với case `Bang Tinh - HĐ 42.xlsx`, công thức template phải được bảo toàn:

```text
Hn = MIN(En:Gn)
In = Dn*Hn
```

`MIN(E:G)` là template formula authority theo quyết định explicit của người dùng; AI/fill engine không tự thay bằng business rule khác hoặc giá trị tĩnh. Khi nhân dòng, relative reference và vùng Tổng cộng/Làm tròn phải được cập nhật an toàn.

Nguồn khảo sát có thể chứa URL, text, hồ sơ nguồn và ảnh/chứng cứ; không giới hạn thành URL-only.

## 8. Generic Document Mapping authority

Word generic vẫn giữ mental model thân thiện: UI không bắt người dùng hiểu Region ID/field path/source collection. Cách cập nhật hiển thị bằng `Tự cập nhật khi dữ liệu thay đổi`, `Chỉ điền lần đầu`, `Người dùng tự chỉnh trong Word`.

AI Template Assistant thực hiện pre-analysis trước bước rà soát; người dùng vẫn có thể click vị trí Word và tự gán dữ liệu khi AI bỏ sót.

## 9. Guardrail

- Design authority không đồng nghĩa product code đã implement.
- AI/Kho tri thức chỉ gợi ý; user quyết định nghiệp vụ chính thức.
- AI Template Assistant không tự publish/silent accept/silent overwrite.
- Workbench + database là nguồn dữ liệu nghiệp vụ chính thức.
- Mỗi thay đổi giá có history/lineage/audit.
- STT tài sản bất biến trong business dataset; template-specific display behavior cần explicit mapping/authority.
- 03 bảng Kết quả thẩm định giá là immutable layout.
- Template báo giá NCC chỉ Word `.docx`.
- Document Workspace không có `Xuất PDF` trong baseline.
- File generated và signed scan là hai artifact khác nhau, có lineage.
- Template/version đã dùng không silent overwrite.
- Generic management không override specialized authority của Word NCC, Word generic hoặc Bảng tính.
- AI không được tự đổi công thức `MIN(E:G)` trong mẫu Bảng tính đã chốt.
- Không đưa dữ liệu thật vào public repository.
