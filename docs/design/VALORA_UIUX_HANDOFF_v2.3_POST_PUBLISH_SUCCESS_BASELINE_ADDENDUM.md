# VALORA UI/UX v2.3 — Đã phát hành — Baseline Addendum

**Status:** DESIGN AUTHORITY / BASELINE  
**Baseline:** `Đã phát hành — Iteration 1`  
**Date:** 01/09/2026  
**Scope:** Post-Publish Success / terminal `PUBLISHED` state

## 1. Vai trò
`Đã phát hành` là success/read-only result state xuất hiện sau khi `Xác nhận phát hành` commit thành công. Đây không phải bước thứ 4 của Publishing và không phải một workflow checkpoint mới.

Authority flow:
```text
Chuẩn bị bộ phát hành
→ Xem lại & xử lý ngoại lệ
→ Xác nhận phát hành [commit boundary]
→ Release Manifest + khóa Document Revision + audit/lineage [system consequence]
→ Đã phát hành [success/read-only state]
```

## 2. Success truth boundary
UI chỉ được hiển thị `Đã phát hành` khi Release Manifest final đã được commit hợp lệ và trạng thái phát hành thành công được xác nhận từ backend. Không dùng optimistic success để giả định commit thành công.

Success state phải phản ánh artifact thật đã commit:
- Release ID thực tế;
- thời điểm phát hành;
- người phát hành;
- số tài liệu thuộc Release Manifest;
- các Document Revision được bind và đã khóa;
- M365 file/version tương ứng nếu có;
- Warning retained/audited nếu có;
- audit/lineage đã ghi nhận.

Nếu commit thất bại hoặc chưa xác định, không route sang success state và không hiển thị `Đã phát hành`.

## 3. Layout authority — Iteration 1
Desktop Fluent 2, Vietnamese-first, read-only.

### Header / success banner
- tiêu đề `Bộ tài liệu đã được phát hành`;
- success banner `Phát hành thành công!`;
- badge trạng thái `ĐÃ PHÁT HÀNH`;
- Release ID, thời điểm phát hành, người phát hành, số tài liệu trong manifest, số Document Revision đã khóa.

### Tiến độ phát hành
Hiển thị 3 bước Publishing đã hoàn thành và result state `Đã phát hành`:
`Chuẩn bị bộ phát hành → Xem lại & xử lý ngoại lệ → Xác nhận phát hành → Đã phát hành`.
Result state cuối không được mô tả như step 4 có thao tác.

### Tóm tắt bản phát hành
Tối thiểu:
- tính toàn vẹn;
- Warning còn lại;
- ngoại lệ bắt buộc;
- lần đồng bộ M365 cuối;
- lịch sử phát hành.

### Bảng tài liệu đã phát hành
Table-first, tối thiểu:
`Tên tài liệu | Loại tài liệu | Document Revision đã phát hành | Trạng thái | Phiên bản M365 | Lần đồng bộ cuối`.

`Trạng thái` đối với revision thuộc release là read-only `Đã khóa`/equivalent. Không edit/unlock/replace revision từ màn này.

### Right rail
- `Thông tin Release`;
- `Tính toàn vẹn bản phát hành`;
- `Lịch sử phát hành`;
- `Hành động`;
- immutable notice.

## 4. Actions
Primary action: `Về Tổng quan hồ sơ`.

Secondary/contextual actions có thể gồm:
- `Xem chi tiết Release Manifest`;
- `Mở tài liệu` / `Mở trong Word`;
- `Xem lịch sử phát hành`;
- `Xem chi tiết` tài liệu/revision/lineage.

Không có `Chỉnh sửa bản phát hành`, `Mở khóa revision`, `Rollback release` hoặc `Xuất PDF`.

## 5. Immutable semantics
Published release và các Document Revision được bind vào release là immutable trong phạm vi release đó. Nếu cần thay đổi sau phát hành:
```text
thay đổi dữ liệu/tài liệu
→ tạo revision mới
→ revalidate/sync theo authority hiện hành
→ tạo release mới
```
Release cũ vẫn giữ nguyên và truy vết được.

## 6. Release history / lineage
Lịch sử phát hành tối thiểu hiển thị:
`Release ID/lần phát hành | thời điểm | người phát hành | số tài liệu | trạng thái`.

Cho phép mở release cũ read-only. Release history không phải đường vòng để sửa release đã phát hành.

Lineage khi xem chi tiết có thể trình bày:
`Template Version → Data Snapshot → Document Revision → M365 file/version → Release Manifest`.

## 7. Global Case State integration
Sau commit thành công:
- canonical stage = `PUBLISHED`;
- completion = terminal/completed theo domain facts;
- primary `next_action = null`;
- resume/default destination = read-only published/release summary hoặc `Tổng quan hồ sơ` tùy route context;
- không tiếp tục hiển thị CTA `Tiếp tục xử lý` như hồ sơ chưa hoàn tất.

## 8. Guardrails
- Success state chỉ sau commit thật.
- Read-only terminal/result surface.
- Không tạo Publishing step mới.
- Không silent unlock/mutate/replace release.
- Không fake Word editor.
- Không Export PDF.
- Warning không đổi thành Blocking sau khi release đã commit; retained warnings được audit/read-only.
- Một primary CTA mỗi context.

## 9. Implementation direction
Post-publish route nên resolve từ Release Manifest thực tế hoặc Global Case State `PUBLISHED`, không từ client-only flag. Read model cần đủ dữ liệu cho release summary, manifest items, locked revisions, M365 version references, integrity checks, warnings and release history.

Nếu implementation thay đổi Release Manifest persistence, locking atomicity, idempotency/retry, partial failure recovery hoặc published-state projection thì cần ADR phù hợp.
