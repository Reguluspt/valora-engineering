# VALORA UI/UX v2.3 — Authority Index

**Status:** Canonical UI/UX reading order for v2.3  
**Purpose:** Ngăn master handoff hoặc iteration cũ override các quyết định mới nhất.

## 1. Thứ tự đọc

1. `VALORA_UIUX_HANDOFF_v2.3_PRICE_EVIDENCE_AUTHORITY_ADDENDUM.md` — authority mới nhất cho thứ tự nguồn giá/chứng cứ, vai trò giá NCC và rule kiểm tra giá Kết quả.
2. `VALORA_UIUX_HANDOFF_v2.3_M365_DOCUMENT_WORKSPACE_BASELINE_ADDENDUM.md` — Microsoft 365 Document Workspace / Bộ tài liệu phát hành.
3. `VALORA_UIUX_HANDOFF_v2.3_FINAL_RESULT_BASELINE_ADDENDUM.md` — Kết quả thẩm định giá, 03 bảng immutable và routing sau NCCQ.
4. `VALORA_UIUX_HANDOFF_v2.3_S17_BASELINE_ADDENDUM.md` — child flow Hoàn tất 01 báo giá NCC theo authority mới nhất của file đó; không được hiểu là readiness toàn hồ sơ nếu mâu thuẫn với authority sau này.
5. `VALORA_UIUX_HANDOFF_v2.3_TM04_BASELINE_ADDENDUM.md` — TM04 Preview/Test fill baseline.
6. `VALORA_UIUX_HANDOFF_v2.3.md` — master handoff; áp dụng cho phần chưa bị các addendum trên supersede.
7. `VALORA_USER_FLOW_MINDMAP_v2.3.md` — flow map hỗ trợ đọc; không override authority nghiệp vụ.

Khi hai nguồn mâu thuẫn, quyết định explicit mới hơn áp dụng trong đúng scope mà nó nêu.

## 2. Price & Evidence authority

Thứ tự ưu tiên nguồn giá/chứng cứ:

```text
1. Giá khảo sát từ Internet
2. Thuyết minh đơn giá
3. Giá trong phần Kết quả thẩm định giá của hồ sơ cũ
```

Giá NCC không phải nguồn chính để xác định Đơn giá thẩm định cuối cùng; giá NCC phục vụ tạo/tái tạo báo giá và đối chiếu.

Rule:

```text
Đơn giá Kết quả định giá <= Đơn giá báo giá NCC dùng để đối chiếu
→ Phù hợp
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

Không có màn NCCQ aggregate trung gian sau `Chọn nhà cung cấp đã xác nhận giá`.

## 4. Baseline visual authority

- NCCQ — Iteration 6.
- TM01 — Iteration 1.
- TM03 — Iteration 1 Word-only.
- TM04 — Iteration 1.
- Hoàn tất 01 báo giá NCC — Iteration 3, scope 01 báo giá / 01 NCC.
- Kết quả thẩm định giá — Iteration 1.
- Microsoft 365 Document Workspace — baseline authority.

## 5. Guardrail

- Mockup/authority không đồng nghĩa product code đã implement.
- Không thay đổi product code từ tài liệu này.
- AI/Kho tri thức chỉ gợi ý; user quyết định nghiệp vụ chính thức.
- Workbench + database là nguồn dữ liệu nghiệp vụ chính thức.
- Mỗi thay đổi giá có history/lineage/audit.
- STT tài sản bất biến theo danh mục gốc.
- 03 bảng Kết quả thẩm định giá là immutable layout.
- Template báo giá NCC chỉ Word `.docx`.
- Document Workspace baseline không có `Xuất PDF`.
- Không đưa dữ liệu khách hàng/NCC/hồ sơ thật vào public repository.