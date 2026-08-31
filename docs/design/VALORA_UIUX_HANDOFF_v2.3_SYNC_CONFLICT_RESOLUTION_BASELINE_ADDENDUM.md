# VALORA UI/UX v2.3 — Xử lý xung đột khi đồng bộ — Baseline Addendum

**Status:** Baseline / Design Authority  
**Iteration:** 1  
**Date:** 31/08/2026

## 1. Quyết định baseline
Mockup `Xử lý xung đột khi đồng bộ — Iteration 1` được nâng thành Baseline / Design Authority. Đây là nhánh có điều kiện giữa `Xem trước kết quả` và `Xác nhận & Đồng bộ`; nếu không có conflict thì bỏ qua hoàn toàn.

## 2. Conflict definition
Conflict tồn tại khi cùng một Managed Region:
- dữ liệu VALORA mới khác giá trị ở snapshot/lần đồng bộ trước; và
- nội dung hiện tại trong Word cũng đã được user chỉnh kể từ lần đồng bộ trước.

Không bên nào tự động thắng.

## 3. Mental flow
```text
Phát hiện conflict
→ Chọn tài liệu/vùng conflict
→ So sánh 3 giá trị
→ User chọn quyết định cho từng vùng
→ Hoàn tất tất cả conflict bắt buộc
→ Áp dụng quyết định vào sync plan
→ Quay lại Xác nhận & Đồng bộ
```

## 4. Layout authority
- Header/breadcrumb + stepper; `Xử lý xung đột` là conditional step.
- Banner giải thích chỉ các vùng conflict cần xử lý; vùng không conflict tiếp tục theo sync plan.
- Trái: danh sách conflict theo tài liệu và theo vùng, số conflict chưa xử lý.
- Giữa: preview Word view-only lớn, highlight đúng Managed Region đang conflict; zoom/page/Open in Word.
- Phải: so sánh `Giá trị lần đồng bộ trước (Snapshot cũ)` / `Dữ liệu VALORA mới` / `Nội dung hiện tại trong Word`, sau đó user chọn cách xử lý.
- Footer: Hủy, quay lại preview, một primary CTA `Áp dụng quyết định & quay lại xác nhận đồng bộ`, kèm progress số vùng đã quyết định.

## 5. Resolution choices
Cho từng vùng conflict, user chọn đúng một:
1. `Dùng dữ liệu VALORA mới` — sync sẽ ghi giá trị VALORA mới vào Managed Region.
2. `Giữ nguyên nội dung trong Word` — vùng đó không bị overwrite bởi VALORA trong lần sync này.
3. `Bỏ qua vùng này trong lần đồng bộ này` — defer vùng đó; phải giữ trạng thái cần xem/cần cập nhật phù hợp, không coi là đã đồng bộ.

Không silent default. Nếu UI preselect một lựa chọn để minh họa, implementation không được hiểu là auto-decision; user decision phải explicit/auditable.

## 6. Completion gate
Primary CTA chỉ được coi là hoàn tất conflict resolution khi mọi conflict bắt buộc trong scope sync đã có quyết định. Quyết định conflict cập nhật **sync plan**, chưa ghi Word và chưa tạo Document Revision tại màn này.

## 7. Audit & version semantics
Mỗi quyết định phải audit được: tài liệu/vùng, ba giá trị so sánh, lựa chọn của user, thời điểm. Document Revision/Microsoft 365 version chỉ được tạo sau bước `Xác nhận & Đồng bộ` thực thi thành công. Published revision/release immutable.

## 8. Guardrails
- Single-user.
- Không auto-win VALORA hoặc Word.
- Không silent overwrite.
- Conflict screen vẫn zero-write đối với Word/document revision.
- Không fake Word editor.
- Không ghi ngoài Managed Regions.
- Một primary CTA.

## 9. ADR
Nếu implementation persist conflict decisions, thay đổi sync-plan transaction boundary, semantics của defer/skip, stale-conflict detection hoặc audit storage thì phải đánh giá ADR riêng trước khi sửa product code.
