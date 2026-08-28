# Prompt bàn giao phiên làm việc tiếp theo — VALORA UI/UX v2.1

Tiếp tục dự án `Reguluspt/valora-engineering`.

## Đọc trước

1. `CODEX.md`
2. `ENGINEERING_GUARDRAILS.md`
3. `docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md`
4. `docs/VALORA_PROJECT_HANDOFF.md`
5. `docs/design/VALORA_UIUX_HANDOFF_v2.1.md`
6. `docs/design/VALORA_DESIGN_BOOK_V1_3_MVP_COMPLETION_ADDENDUM.md`
7. `docs/design/VALORA_DESIGN_BOOK_V1_4_ADAPTIVE_INTAKE_KNOWLEDGE_MEMORY_ADDENDUM.md`
8. `docs/design/VALORA_EXCEL_IMPORT_STAGING_CONTRACT.md`
9. `docs/design/VALORA_LIVE_WORKBENCH_ASSET_LINES_API_CONTRACT.md`

## Baseline mới nhất

- Single-user.
- Máy móc thiết bị.
- Phương pháp so sánh.
- Không khảo sát hiện trạng.
- AI/Kho tri thức chỉ gợi ý.
- S08 không có màn hình riêng; rà soát tích hợp S02 `Quản lý yêu cầu sơ bộ`.
- Sau rà soát đạt, tạo file kết quả sơ bộ là bản sao Excel khách hàng + 02 cột `Đơn giá đề xuất`, `Thành tiền`.
- Không có workflow `Ghi nhận đã gửi/trao đổi → Chờ khách hàng phản hồi → Ghi nhận phản hồi`.
- Sau khi đã tạo file kết quả sơ bộ, CTA chính là `Chuyển sang thẩm định chính thức`.
- `Không tiếp tục` vẫn được giữ để đóng Pre-case và bảo toàn lịch sử.

## Luồng hiện hành

```text
Quản lý yêu cầu sơ bộ
→ Tạo yêu cầu sơ bộ
→ Upload & Mapping Excel
→ Phân tích danh mục
→ Quay lại Quản lý yêu cầu sơ bộ
→ Rà soát tích hợp
→ Tạo file kết quả sơ bộ
→ Chuyển sang thẩm định chính thức
→ Các bước nghiệp vụ tiếp theo
```

## Quy tắc giá

```text
Đơn giá KH dự kiến
→ Giá tham chiếu Kho tri thức
→ Giá thị trường tham khảo
→ Vận chuyển (%)
→ Đơn giá đề xuất
```

`Đơn giá đề xuất = Giá thị trường × (1 + Vận chuyển % / 100)`.

Không hiển thị `Chênh lệch`, `Chi phí vận chuyển`, `Giá sau vận chuyển`.

`Thuyết minh đơn giá` có thể là căn cứ duy nhất của một dòng. Không cho hoàn tất nếu còn dòng chưa xác định được giá.

## Nhiệm vụ tiếp theo

Đi sâu vào **S09 — Chuyển sang thẩm định chính thức**:

- mục tiêu người dùng;
- điều kiện vào;
- dữ liệu nào prefill từ Pre-case;
- thông tin khách hàng/pháp nhân/hợp đồng cần nhập ở bước này;
- xử lý danh mục có thay đổi hay không;
- cách tái sử dụng file kết quả sơ bộ, nguồn giá và snapshot;
- loading/empty/error/warning;
- CTA/confirm;
- snapshot/audit/lineage khi chuyển;
- dựng mockup bám đúng design system Valora.

Không sửa code sản phẩm khi chưa có yêu cầu. Phân biệt rõ thiết kế mục tiêu và trạng thái đã implement.
