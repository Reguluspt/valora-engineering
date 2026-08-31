# VALORA UI/UX v2.3 — Xác nhận & Lưu template tùy biến — Baseline Addendum

**Status:** Baseline / Design Authority  
**Iteration:** 1  
**Date:** 31/08/2026

## 1. Quyết định baseline
Mockup `Xác nhận & Lưu template tùy biến — Iteration 1` được nâng thành Baseline / Design Authority. Đây là bước 4/4 của flow AI custom-template hiện hành.

## 2. Flow authority
```text
Tải file & phân tích → Đề xuất mapping → Test fill (xem trước) → Xác nhận & Lưu template
```

Bước này chỉ được vào sau Test fill. Kết quả validation từ Test fill được mang sang để user ra quyết định cuối.

## 3. Layout authority
- Trái: thông tin Template Version dự kiến, thống kê vùng dữ liệu, trạng thái Test fill.
- Giữa: preview Word view-only lớn của kết quả đã test fill, có zoom/page/full-screen và legend vùng dữ liệu.
- Phải: validation `Blocking / Warning / Info`, chi tiết vấn đề và `Phạm vi sử dụng template`.
- Footer: `Hủy`, `Quay lại: Test fill`, một primary CTA `Xác nhận & Lưu template`.
- Không fake Word editor.

## 4. Validation gate
- `Blocking > 0`: không cho lưu Template Version.
- `Blocking = 0`: user có thể lưu; Warning phải được nhìn thấy nhưng không tự động Blocking.
- Info chỉ cung cấp thông tin.
- Không silent sửa mapping, repeating region, nội dung cố định hoặc dữ liệu nguồn để làm validation pass.

## 5. Phạm vi sử dụng
User phải thấy rõ hai lựa chọn:
1. `Chỉ sử dụng cho hồ sơ này` — mặc định.
2. `Lưu vào thư viện mẫu để tái sử dụng` — explicit opt-in.

Không auto-promote template hồ sơ thành library/global template. Việc đổi scope là quyết định của user.

## 6. Save semantics
Khi user nhấn `Xác nhận & Lưu template`:
- lưu Template Version với mapping/Managed Regions đã được user xác nhận;
- ghi nhận kết quả Test fill/validation làm provenance của lần lưu;
- giữ nguyên file nguồn và nội dung ngoài vùng VALORA quản lý;
- không tự tạo/publish Document Revision;
- sau khi lưu thành công, template sẵn sàng quay về `Tạo & Xem lại bộ tài liệu hồ sơ` để dùng trong batch generation.

## 7. Guardrails
- AI advisory; user quyết định cuối.
- Không silent accept/save/promote/publish.
- Custom field không tự promote thành canonical field.
- Một primary CTA.
- Vietnamese-first; không phơi technical internals.

## 8. ADR
Nếu implementation thay đổi transaction boundary của Template Version save, provenance của Test fill, scope promotion từ case-only sang library, hoặc rollback/idempotency của save thì phải đánh giá ADR riêng trước khi sửa product code.
