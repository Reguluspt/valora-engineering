# VALORA UI/UX v2.3 — Chuẩn bị bộ phát hành — Baseline Addendum

**Status:** Baseline / Design Authority  
**Iteration:** 1  
**Date:** 31/08/2026

## 1. Quyết định baseline
Mockup `Chuẩn bị bộ phát hành — Iteration 1` được nâng thành Baseline / Design Authority.

Baseline này **supersede flow Publishing 5 bước cũ**:
`Chọn tài liệu → Kiểm tra tình trạng → Xem bộ tài liệu → Xác nhận phát hành → Khóa phiên bản đã phát hành`.

Flow Publishing authority mới được rút gọn thành:
```text
Chuẩn bị bộ phát hành
→ Xem lại & xử lý ngoại lệ
→ Xác nhận phát hành
```

`Khóa phiên bản đã phát hành` không còn là một bước thao tác riêng; đó là hậu quả hệ thống của hành động phát hành thành công.

## 2. Mental model
VALORA tự chuẩn bị bộ phát hành từ revision mới nhất đủ điều kiện. User không phải chọn thủ công từng tài liệu bình thường; user chủ yếu review **ngoại lệ**.

```text
Revision mới nhất + readiness
→ Auto-select tài liệu đủ điều kiện
→ Highlight Cần xem lại / Có lỗi
→ User điều chỉnh nếu cần
→ Tiếp tục xem lại ngoại lệ
```

## 3. Layout authority
- Header/breadcrumb trong `Bộ tài liệu hồ sơ → Phát hành bộ tài liệu → Chuẩn bị bộ phát hành`.
- Summary cards: `Sẵn sàng phát hành (auto-selected) / Cần xem lại / Có lỗi / Không thay đổi / Tổng tài liệu`.
- Banner giải thích cách hệ thống chọn tài liệu.
- Bảng `Danh sách tài liệu sẽ phát hành` với tối thiểu: `Tên tài liệu | Loại tài liệu | Revision (VALORA) | Trạng thái | Lần đồng bộ gần nhất | Chọn để phát hành`.
- Preview nhanh tài liệu ở cùng workspace, view-only, có `Mở trong Word`.
- Panel phải: Release dự kiến, ngày phát hành dự kiến, breakdown trạng thái, danh sách điểm cần chú ý.
- Footer có Hủy và một primary CTA theo context.

## 4. Auto-selection authority
VALORA tự động chọn revision mới nhất đủ điều kiện phát hành. User có thể bỏ chọn tài liệu nếu không muốn đưa vào release.

Không auto-select tài liệu có Blocking/error. `Cần xem lại` được đưa thành exception cần user xem trước khi phát hành. `Không thay đổi` có thể dùng revision hiện hành nếu revision đó vẫn hợp lệ theo release readiness rule; không bắt buộc tạo revision mới.

Auto-selection là hỗ trợ giảm thao tác, không phải silent publish. User vẫn xác nhận release ở bước cuối.

## 5. Exception-first UX
Mục tiêu của bước này là giảm thao tác:
- không tick từng tài liệu bình thường;
- không có màn `Kiểm tra tình trạng` riêng;
- không có màn `Xem bộ tài liệu` riêng chỉ để lặp lại trạng thái;
- chỉ đưa user sang `Xem lại & xử lý ngoại lệ` khi có tài liệu cần chú ý;
- nếu không có ngoại lệ, flow có thể đi nhanh đến xác nhận phát hành theo readiness authority.

## 6. Publishing semantics
Release vẫn bind chính xác các Document Revision được chọn vào Release Manifest. Sau phát hành thành công, các revision nằm trong release được khóa/immutable theo authority hiện hành.

Không có luồng `Xuất PDF` trong Publishing baseline.

## 7. Superseded proposal
Mockup `Chọn tài liệu để phát hành — Iteration 1` trước đó là Design Proposal và bị supersede bởi baseline này. Không dùng lại flow chọn thủ công + 5 bước như authority mới.

## 8. Guardrails
- Single-user.
- Auto-select nhưng không auto-publish.
- Không silent thêm tài liệu có lỗi vào release.
- Không fake Word editor.
- Một primary CTA mỗi context.
- Published release/revisions immutable.
- Không export PDF.

## 9. ADR
Nếu implementation thay đổi release-readiness computation, auto-selection persistence, Release Manifest binding, locking transaction, hoặc partial publish semantics thì phải đánh giá ADR riêng trước khi sửa product code.
