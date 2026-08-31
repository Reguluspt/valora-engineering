# VALORA UI/UX v2.3 — Xem lại & xử lý ngoại lệ — Baseline Addendum

**Status:** Baseline / Design Authority  
**Iteration:** 1  
**Date:** 31/08/2026

## 1. Quyết định baseline
Mockup `Xem lại & xử lý ngoại lệ — Iteration 1` được nâng thành Baseline / Design Authority. Đây là bước 2/3 của Publishing simplified flow, sau `Chuẩn bị bộ phát hành` và trước `Xác nhận phát hành`.

## 2. Mục tiêu
Exception-first UX: user không rà lại toàn bộ tài liệu đã `Sẵn sàng`. Màn hình chỉ tập trung các tài liệu cần quyết định hoặc xử lý trước release.

## 3. Routing authority
```text
Chuẩn bị bộ phát hành
→ Xem lại & xử lý ngoại lệ
   → chọn ngoại lệ
   → xem nguyên nhân + preview
   → xử lý hoặc loại khỏi release
   → hoàn tất các ngoại lệ bắt buộc
→ Xác nhận phát hành
→ Release Manifest + khóa revision đã phát hành [system consequence]
```

## 4. Layout authority
- Header/breadcrumb + stepper 3 bước; bước 2 active.
- Summary cards: `Cần xem lại / Có lỗi (bắt buộc xử lý) / Cảnh báo (không chặn)` + hướng dẫn.
- Trái: `Danh sách ngoại lệ`, filter/tab theo loại, tài liệu + revision + trạng thái. Tài liệu `Sẵn sàng` được ẩn khỏi task list.
- Giữa: preview tài liệu view-only lớn; highlight vùng/vấn đề liên quan; `Mở trong Word` là secondary action.
- Phải: `Chi tiết & lý do ngoại lệ`, vấn đề, thông tin đồng bộ/revision và lựa chọn xử lý.
- Footer: progress ngoại lệ bắt buộc đã xử lý + một primary CTA `Tiếp tục: Xác nhận phát hành`.

## 5. Exception semantics
- `Có lỗi / Blocking`: không được giữ tài liệu đó trong release ở trạng thái lỗi. User phải cập nhật/sửa rồi revalidate hoặc loại tài liệu khỏi release.
- `Cần xem lại`: user review và đưa ra quyết định phù hợp trước khi tiếp tục nếu rule yêu cầu.
- `Cảnh báo`: không tự Blocking; user có thể giữ tài liệu trong release sau khi đã nhìn thấy cảnh báo theo rule hiện hành.
- `Sẵn sàng`: không phải việc cần làm ở màn này; đã được xử lý ở Release Preparation.

## 6. Actions
Các action authority theo ngữ cảnh:
1. `Mở tài liệu để cập nhật` — mở Microsoft 365/Word để xử lý nguồn vấn đề; sau khi quay lại phải revalidate trạng thái hiện tại.
2. `Loại khỏi bộ phát hành` — bỏ tài liệu khỏi Release Manifest dự kiến của lần này.
3. `Giữ nguyên và phát hành` — chỉ khả dụng với ngoại lệ không Blocking; là quyết định explicit, không silent bypass.

Không fake Word editor và không sửa nội dung Word trực tiếp trong VALORA.

## 7. Completion gate
CTA sang `Xác nhận phát hành` chỉ enabled khi:
- mọi Blocking trong phạm vi release đã được xử lý hoặc tài liệu tương ứng đã bị loại;
- release plan chưa stale;
- các quyết định bắt buộc đã được ghi nhận.

Nếu document/revision/readiness thay đổi trong lúc user review, VALORA phải revalidate trước khi cho tiếp tục.

## 8. Audit & release semantics
Quyết định xử lý ngoại lệ phải audit được: tài liệu, revision, vấn đề, quyết định user, thời điểm. Màn này chưa publish, chưa tạo Release Manifest final và chưa khóa revision. Việc tạo Release Manifest + khóa revision chỉ xảy ra sau `Xác nhận phát hành` thành công.

## 9. Guardrails
- Single-user.
- Exception-first; giảm thao tác bình thường.
- Không silent bypass Blocking/cảnh báo.
- Không silent publish.
- Không fake Word editor.
- Không Xuất PDF.
- Một primary CTA mỗi context.

## 10. ADR
Nếu implementation persist exception decisions, thay đổi release-plan stale detection, revalidation after Word edit, exclusion semantics, hoặc transaction boundary của Release Manifest/locking thì phải đánh giá ADR riêng trước khi sửa product code.
