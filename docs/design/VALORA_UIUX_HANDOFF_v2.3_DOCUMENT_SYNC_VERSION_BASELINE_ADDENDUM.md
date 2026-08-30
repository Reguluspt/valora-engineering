# VALORA UI/UX v2.3 — Đồng bộ dữ liệu & Quản lý phiên bản tài liệu — Baseline Addendum

**Status:** Baseline / Design Authority  
**Iteration:** 1  
**Ngày chốt:** 30/08/2026  
**Scope:** Microsoft 365 Document Workspace — UX đồng bộ dữ liệu và quản lý phiên bản tài liệu Word sau khi dữ liệu VALORA thay đổi.

## 1. Mục tiêu

Giúp người dùng nghiệp vụ, kể cả người không rành IT, hiểu rõ dữ liệu nào đã thay đổi, nội dung nào trong tài liệu Word sẽ được cập nhật và phiên bản tài liệu nào được tạo/ghi nhận sau thao tác đồng bộ.

UI ưu tiên ngôn ngữ nghiệp vụ: `Dữ liệu mới`, `Nội dung hiện tại`, `Phiên bản tài liệu`, `Cần cập nhật`, `Cập nhật vào Word`. Các khái niệm kỹ thuật Data Snapshot, Document Revision và Microsoft 365 file version vẫn được lưu trong domain/audit nhưng không phải mental model chính.

## 2. Flow baseline

```text
1. Xem những gì đã thay đổi
→ 2. Xem chi tiết khác biệt
→ 3. Chọn nội dung muốn cập nhật
→ 4. Cập nhật vào Word & tạo/ghi nhận phiên bản
```

Không silent sync. Người dùng phải biết và chọn nội dung sẽ được cập nhật trước khi ghi vào Word.

## 3. Layout authority

Desktop-first, Fluent 2, data-heavy nhưng đơn giản hóa cho người dùng nghiệp vụ.

```text
Header + trạng thái tài liệu
→ Quy trình 4 bước đơn giản
→ Danh sách vùng có dữ liệu thay đổi
→ Preview tài liệu Word
→ Tóm tắt khác biệt + dữ liệu mới nhất từ VALORA + lịch sử phiên bản
→ Footer actions
```

Preview chỉ để xem, không phải Word editor. Chỉnh sửa narrative tiếp tục dùng `Mở trong Word`.

## 4. Trạng thái và mức thay đổi

Tài liệu có thể hiển thị `Cần cập nhật` khi dữ liệu VALORA mới hơn dữ liệu đã đồng bộ vào tài liệu.

Mỗi vùng có thể biểu diễn mức thay đổi bằng ngôn ngữ dễ hiểu:

```text
Thay đổi nhiều
Thay đổi một phần
Thay đổi nhỏ
Không thay đổi
```

Các vùng không thay đổi không cần được ghi lại chỉ để tạo cảm giác đã đồng bộ.

## 5. Chọn nội dung cập nhật

Danh sách vùng thay đổi phải cho phép chọn từng vùng hoặc chọn tất cả vùng cần cập nhật. Người dùng có thể xem chi tiết trước khi quyết định.

Chỉ các managed regions được chọn mới được cập nhật. Narrative ngoài managed regions và phần người dùng tự biên tập trong Word phải giữ nguyên.

Nếu phát hiện người dùng đã sửa nội dung bên trong managed region, hệ thống phải đưa người dùng vào bước xem khác biệt/xử lý xung đột; không silent overwrite.

## 6. Đồng bộ và phiên bản

Lineage chuẩn tiếp tục là:

```text
Template Version
→ Data Snapshot
→ Document Revision
→ Microsoft 365 file/version
```

Bề mặt user-facing ưu tiên `Phiên bản tài liệu` như `rev0`, `rev1`, `rev2` hoặc naming scheme được hệ thống áp dụng. Lịch sử phải cho biết tối thiểu phiên bản, thời điểm, người thao tác và trạng thái đồng bộ.

Baseline không đồng nhất Document Revision với Microsoft 365 file version trong domain. Hai lớp có thể liên kết nhưng phải được truy vết riêng trong implementation/audit.

Khi thao tác cập nhật thành công, hệ thống phải ghi nhận snapshot dữ liệu dùng cho lần sync, revision tài liệu tương ứng và file/version Microsoft 365 liên quan. Không silent mutate revision đã phát hành.

## 7. Hành động baseline

Các action chính:

```text
Mở trong Word
Cập nhật vào Word
Xem chi tiết
Chọn tất cả / Bỏ chọn tất cả
Lưu nháp lựa chọn
Tiếp tục
Xem tất cả phiên bản
```

Primary CTA phải phản ánh đúng bước hiện tại. Không tạo nhiều primary CTA cạnh tranh.

## 8. Guardrails

- Không xây fake Word editor trong VALORA.
- Không silent sync.
- Không overwrite narrative ngoài managed regions.
- Không silent overwrite nội dung user đã sửa trong managed region.
- Không silent mutate tài liệu/revision đã phát hành.
- Không bắt người dùng hiểu Snapshot ID, Revision ID hoặc DriveItem version để hoàn thành tác vụ.
- Lịch sử/version phải giữ lineage và audit.
- Trạng thái `Cần cập nhật` phải bắt nguồn từ khác biệt dữ liệu có thể truy vết, không chỉ là badge thủ công.
- File Word generated và signed scan vẫn là hai artifact khác nhau.

## 9. Visual authority

Mockup `Đồng bộ dữ liệu & Quản lý phiên bản tài liệu — Iteration 1` được người dùng explicit nâng thành Baseline ngày 30/08/2026.

Visual baseline gồm: header trạng thái `Cần cập nhật`; quy trình 4 bước; danh sách vùng thay đổi; preview Word với highlight vùng; panel tóm tắt khác biệt; dữ liệu mới nhất từ VALORA; lịch sử `rev2/rev1/rev0`; quick tips; footer `Mở trong Word / Lưu nháp lựa chọn / Tiếp tục`.

## 10. Quan hệ với Managed Regions Baseline

Baseline này kế thừa toàn bộ authority của `Managed Regions — Báo cáo thẩm định giá — Iteration 1` và đặc tả sâu hơn UX khi dữ liệu thay đổi và tài liệu cần sync/version.

Nếu có xung đột trong đúng scope sync/version, addendum này là quyết định explicit mới hơn. Nó không mở rộng visual baseline Managed Regions sang Chứng thư nếu chưa có quyết định explicit riêng.

## 11. ADR

Đây là UI/UX Design Authority, chưa đồng nghĩa product code đã implement. Không phát sinh ADR chỉ vì nâng mockup thành baseline.

Nếu implementation thay đổi persistence contract của Data Snapshot, Document Revision, Microsoft 365 version mapping, conflict detection, managed-region sync hoặc immutable published revision, phải đánh giá ADR kỹ thuật riêng trước khi sửa product code.
