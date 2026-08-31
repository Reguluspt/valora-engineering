# VALORA UI/UX v2.3 — Xác nhận phát hành — Baseline Addendum

**Status:** Baseline / Design Authority  
**Iteration:** 1  
**Date:** 31/08/2026

## 1. Quyết định baseline
Mockup `Xác nhận phát hành — Iteration 1` được nâng thành Baseline / Design Authority. Đây là bước UI 3/3 và là write/commit boundary của Publishing simplified flow.

## 2. Mental flow
```text
Chuẩn bị bộ phát hành
→ Xem lại & xử lý ngoại lệ
→ Xác nhận phát hành [commit boundary]
→ hệ thống tạo Release Manifest
→ khóa các Document Revision thuộc release
→ ghi audit
```

Không có bước UI `Khóa phiên bản` riêng. Không có `Xuất PDF`.

## 3. Layout authority
- Header/breadcrumb + stepper 3 bước, bước 3 active.
- `Thông tin phát hành dự kiến`: Release ID dự kiến, ngày phát hành dự kiến, ghi chú tùy chọn, người phát hành.
- `Tóm tắt bộ tài liệu sẽ phát hành`: số tài liệu sẽ phát hành, cảnh báo còn lại, tài liệu bị loại, tổng tài liệu, tổng revision.
- Bảng `Danh sách tài liệu sẽ phát hành`: tên, loại, Document Revision, trạng thái, lần đồng bộ gần nhất; mặc định chỉ cần preview subset + xem tất cả.
- Khối `Ngoại lệ đã xử lý`: số Blocking/Cần xem lại/Cảnh báo ban đầu và kết quả xử lý.
- Khối `Tính toàn vẹn & điều kiện phát hành`: Managed Regions sync thành công, revision hợp lệ, không xung đột phiên bản, tài liệu sẵn sàng.
- Panel phải `Tóm tắt Release` + `Hệ quả sau khi phát hành` + warning immutable.
- Footer: Hủy, quay lại bước ngoại lệ, một primary CTA `Xác nhận phát hành`.

## 4. Commit gate
CTA `Xác nhận phát hành` chỉ enabled khi:
- Blocking = 0 trong release scope;
- mọi ngoại lệ bắt buộc đã xử lý;
- các revision được chọn vẫn hợp lệ và release plan chưa stale;
- không có unresolved version conflict;
- mọi tài liệu giữ trong release đạt readiness theo authority hiện hành.

Nếu trạng thái thay đổi sau lần review gần nhất, hệ thống phải revalidate trước commit; không silent publish với release plan stale.

## 5. Commit semantics
Khi user xác nhận thành công, hệ thống thực hiện một hành động nghiệp vụ phát hành:
1. tạo Release Manifest final, bind chính xác các Document Revision đã chọn;
2. khóa/immutable các Document Revision thuộc release;
3. ghi audit event phát hành và lineage;
4. ghi trạng thái release thành công.

Các tài liệu đã bị loại không thuộc manifest và không bị khóa bởi release này. Warning non-Blocking còn lại phải được phản ánh/audit theo rule hiện hành.

## 6. Release ID semantics
Release ID hiển thị trước commit là `dự kiến/reserved`. Implementation không được coi một ID minh họa trên mockup là schema cứng. Nếu commit thất bại, không được hiển thị release như đã phát hành thành công.

## 7. Failure semantics
Không được để UI báo `Đã phát hành` khi Release Manifest chưa được commit hợp lệ. Nếu kiến trúc cho phép partial commit giữa manifest/locking/audit thì phải có transaction/recovery authority qua ADR; UI phải phản ánh trạng thái thực tế và không che lỗi.

## 8. Guardrails
- Single-user.
- Explicit final confirmation; không auto-publish.
- Không silent bypass Warning/Blocking.
- Không fake Word editor.
- Không `Xuất PDF`.
- Lock revision là system consequence, không phải bước UI.
- Published release/revision immutable.
- Một primary CTA mỗi context.

## 9. ADR
Release Manifest transaction boundary, Release ID reservation, locking atomicity, retry/idempotency, failure recovery và audit commit semantics cần ADR nếu implementation chưa có authority tương ứng hoặc thay đổi persistence/architecture.
