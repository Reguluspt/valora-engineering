# VALORA UI/UX v2.3 — Authority Index

**Status:** Canonical UI/UX reading order for v2.3  
**Purpose:** Ngăn iteration/addendum cũ override các quyết định đã được consolidate hoặc authority mới hơn.

## 1. Thứ tự đọc hiện hành

1. `VALORA_UIUX_HANDOFF_v2.3.md` — **canonical master đã consolidate** toàn bộ authority hiện hành tại thời điểm commit consolidation.
2. `VALORA_UIUX_HANDOFF_v2.3_GENERIC_DOCUMENT_MAPPING_BASELINE_ADDENDUM.md` — **authority mới nhất cho Mapping Template tài liệu generic — Iteration 2**, scope chính `Microsoft 365 Document Workspace / 03_Hợp đồng`; supersede Iteration 1 generic thiên về kỹ thuật/admin và supersede câu roadmap cũ coi mapping `03_Hợp đồng` vẫn chưa được baseline.
3. `VALORA_UIUX_HANDOFF_v2.3_PRICE_EVIDENCE_AUTHORITY_ADDENDUM.md` — companion để truy vết quyết định nguồn giá/chứng cứ và rule đối chiếu giá.
4. `VALORA_UIUX_HANDOFF_v2.3_FINAL_RESULT_BASELINE_ADDENDUM.md` — companion cho Kết quả thẩm định giá, 03 bảng immutable và routing sau NCCQ.
5. `VALORA_UIUX_HANDOFF_v2.3_M365_DOCUMENT_WORKSPACE_BASELINE_ADDENDUM.md` — companion Microsoft 365 Document Workspace / Bộ tài liệu phát hành.
6. `VALORA_UIUX_HANDOFF_v2.3_S17_BASELINE_ADDENDUM.md` — companion lịch sử của child flow Hoàn tất 01 báo giá NCC; không được dùng để chèn S17 readiness toàn hồ sơ vào routing mới.
7. `VALORA_UIUX_HANDOFF_v2.3_TM04_BASELINE_ADDENDUM.md` — companion TM04 Preview/Test fill baseline.
8. `VALORA_USER_FLOW_MINDMAP_v2.3.md` — flow map hỗ trợ đọc; không override authority nghiệp vụ.

Khi companion/addendum có câu lịch sử mâu thuẫn với canonical master đã consolidate, **master hiện hành thắng**, ngoại trừ quyết định explicit mới hơn được người dùng chốt sau commit consolidation. Trong scope Mapping Template tài liệu generic, addendum Iteration 2 ở mục 2 là quyết định explicit mới hơn và được ưu tiên áp dụng.

## 2. Price & Evidence authority

```text
1. Giá khảo sát từ Internet
2. Thuyết minh đơn giá
3. Giá trong phần Kết quả thẩm định giá của hồ sơ cũ
```

Giá NCC không phải nguồn chính để xác định Đơn giá thẩm định cuối cùng; giá NCC phục vụ tạo/tái tạo báo giá và đối chiếu.

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
- **Mapping Template tài liệu generic — Iteration 2 — baseline/design authority; UX thân thiện cho người nghiệp vụ không rành IT.**

## 5. Generic Document Mapping authority

Mental model authority:

```text
Chọn mẫu Word
→ Chọn dữ liệu nghiệp vụ
→ Click vị trí cần điền trong Word
→ VALORA tạo mapping phía sau
→ Kiểm tra & hoàn tất
```

UI không bắt người dùng nghiệp vụ hiểu `Region ID`, field path, source collection hoặc repeating-region configuration kỹ thuật.

Các cách cập nhật hiển thị bằng ngôn ngữ nghiệp vụ:

```text
Tự cập nhật khi dữ liệu thay đổi
Chỉ điền lần đầu
Người dùng tự chỉnh trong Word
```

Bảng danh mục nhiều dòng dùng mental model `Đây là dòng mẫu danh mục → gán từng cột`, trong khi repeating-region semantics được engine quản lý phía sau.

Baseline generic áp dụng trước hết cho `03_Hợp đồng`; định hướng một Document Template Engine dùng chung nhưng không tự động override authority TM03/TM04 của báo giá NCC.

## 6. Guardrail

- Design authority không đồng nghĩa product code đã implement.
- AI/Kho tri thức chỉ gợi ý; user quyết định nghiệp vụ chính thức.
- Workbench + database là nguồn dữ liệu nghiệp vụ chính thức.
- Mỗi thay đổi giá có history/lineage/audit.
- STT tài sản bất biến theo danh mục gốc.
- 03 bảng Kết quả thẩm định giá là immutable layout.
- Template báo giá NCC chỉ Word `.docx`.
- Document Workspace không có `Xuất PDF` trong baseline.
- File generated và file scan signed là hai artifact khác nhau, có lineage.
- Generic document mapping chỉ khóa UX/mental model/domain boundary; không khóa implementation technology cụ thể.
- Sync chỉ cập nhật vùng VALORA quản lý và không overwrite narrative người dùng trong Word.
- Tài liệu đã phát hành không silent mutate; thay đổi phải đi qua revision/version lifecycle.
- Không đưa dữ liệu khách hàng/NCC/hồ sơ thật vào public repository.
