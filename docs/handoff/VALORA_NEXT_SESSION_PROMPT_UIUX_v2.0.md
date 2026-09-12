# Prompt bàn giao phiên làm việc tiếp theo — VALORA UI/UX v2.0

Tiếp tục dự án Valora trong repository `Reguluspt/valora-engineering`.

## Đọc trước

1. `CODEX.md`
2. `ENGINEERING_GUARDRAILS.md`
3. `docs/design/VALORA_DESIGN_AUTHORITY_INDEX.md`
4. `docs/VALORA_PROJECT_HANDOFF.md`
5. `docs/design/VALORA_UIUX_HANDOFF_v2.0.md`
6. `docs/design/VALORA_DESIGN_BOOK_V1_3_MVP_COMPLETION_ADDENDUM.md`
7. `docs/design/VALORA_DESIGN_BOOK_V1_4_ADAPTIVE_INTAKE_KNOWLEDGE_MEMORY_ADDENDUM.md`
8. `docs/design/VALORA_EXCEL_IMPORT_STAGING_CONTRACT.md`
9. `docs/design/VALORA_LIVE_WORKBENCH_ASSET_LINES_API_CONTRACT.md`

## Baseline sản phẩm

- Single-user.
- Máy móc thiết bị.
- Phương pháp so sánh.
- Không khảo sát hiện trạng.
- Kho tri thức/AI chỉ gợi ý; người dùng xác nhận.

## Luồng Pre-case đã chốt

```text
Quản lý yêu cầu sơ bộ
→ Tạo yêu cầu sơ bộ
→ Upload & Mapping Excel
→ Phân tích danh mục
→ Kho tri thức / Nguồn giá / Thuyết minh
→ Giá thị trường
→ Vận chuyển (%)
→ Đơn giá đề xuất
→ quay lại Quản lý yêu cầu sơ bộ
→ Rà soát tích hợp
→ Tạo file kết quả sơ bộ
→ Ghi nhận đã gửi/trao đổi
→ Chờ phản hồi
→ Khách hàng chấp thuận
→ Chuyển thành hồ sơ chính thức
```

## Quyết định v2.0 quan trọng

- S08 không còn là màn hình riêng.
- Rà soát được tích hợp vào S02 `Quản lý yêu cầu sơ bộ` bằng panel/drawer.
- Không tạo file nếu còn dòng chưa có giá/chưa xác nhận.
- `Thuyết minh đơn giá` có thể là căn cứ duy nhất.
- `Thành tiền = SL × Đơn giá đề xuất`.
- File kết quả sơ bộ là bản sao của file Excel khách hàng, bổ sung đúng 02 cột `Đơn giá đề xuất` và `Thành tiền` tại vùng bảng đã mapping.
- File nguồn không bị ghi đè; output có version + lineage.
- Tạo file chưa đồng nghĩa đã gửi khách và chưa tự chuyển sang `Chờ khách hàng phản hồi`.

## Mockup đã duyệt

1. Quản lý yêu cầu sơ bộ.
2. Tạo yêu cầu sơ bộ.
3. Upload & Mapping Excel.
4. Phân tích danh mục.
5. Panel Kho tri thức.
6. Panel Nguồn giá Internet.
7. Thêm nguồn giá.
8. Quản lý yêu cầu sơ bộ — panel `Rà soát & tạo file kết quả sơ bộ`.

## Nhiệm vụ tiếp theo

Thiết kế sâu bước **Ghi nhận đã gửi/trao đổi → Chờ khách hàng phản hồi → Ghi nhận phản hồi**.

Cần chốt:

- cách ghi nhận file/version nào đã gửi khách;
- ngày trao đổi và ghi chú;
- có/không attachment bổ sung;
- outcome phản hồi: chấp thuận / yêu cầu điều chỉnh / không tiếp tục;
- khi yêu cầu điều chỉnh, cách quay lại đúng danh mục/giá và tạo version file kết quả mới;
- timeline lịch sử trao đổi;
- CTA vào `S09 — Chuyển thành hồ sơ` khi khách hàng chấp thuận;
- loading/empty/error/warning/confirm states.

Không sửa code sản phẩm nếu người dùng chưa yêu cầu. Trao đổi bằng tiếng Việt, xưng em/gọi anh, desktop-first và luôn phân biệt rõ thiết kế mục tiêu với trạng thái đã implement.
