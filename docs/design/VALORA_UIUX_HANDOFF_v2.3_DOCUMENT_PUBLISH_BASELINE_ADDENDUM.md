# VALORA UI/UX v2.3 — Phát hành bộ tài liệu Baseline Addendum

**Screen:** Phát hành bộ tài liệu  
**Iteration:** 1  
**Status:** Baseline / Design Authority  
**Scope:** Microsoft 365 Document Workspace — release package selection, readiness, preview, confirmation, immutable release lineage.

## 1. Mental model

UI dùng ngôn ngữ nghiệp vụ, không yêu cầu người dùng hiểu Snapshot/Revision/DriveItem ID:

```text
1. Chọn tài liệu
→ 2. Kiểm tra tình trạng
→ 3. Xem bộ tài liệu
→ 4. Xác nhận phát hành
→ Khóa phiên bản đã phát hành
```

Không tạo workflow KSCL/phê duyệt nhiều cấp mới. Validation vẫn phân tán tại dependency thực tế.

## 2. Layout authority

Desktop-first, Fluent 2, Vietnamese-first. Màn hình gồm:

- breadcrumb + tiêu đề `Phát hành bộ tài liệu`;
- stepper 4 bước;
- bảng chọn tài liệu là vùng chính;
- panel phải tóm tắt tình trạng bộ tài liệu, thông tin hồ sơ, lịch sử phát hành, giải thích trạng thái;
- notice giải thích điều xảy ra sau khi phát hành;
- footer actions với một primary CTA theo bước.

Bảng tối thiểu:

```text
Tài liệu | Loại tài liệu | Trạng thái | Lần cập nhật |
Phiên bản | Người cập nhật | Chọn | Xem chi tiết
```

## 3. Trạng thái user-facing

```text
Sẵn sàng
Cần cập nhật
Chưa hoàn tất
Không áp dụng
Đã phát hành
```

`Cần cập nhật`: dữ liệu VALORA đã thay đổi và tài liệu managed cần sync lại trước khi phát hành.

`Chưa hoàn tất`: còn Blocking/dependency chưa xử lý.

`Không áp dụng`: artifact không tham gia managed-region readiness theo cùng semantics; không tự suy diễn rằng mọi PDF đều hợp lệ hoặc bắt buộc được phát hành.

## 4. Readiness và selection

- Chỉ tài liệu đáp ứng điều kiện phát hành của loại tài liệu mới được chọn.
- Tài liệu `Cần cập nhật` hoặc `Chưa hoàn tất` phải nêu lý do và CTA đi xử lý tại dependency thực tế.
- Có thể chọn một tập con các tài liệu sẵn sàng; không mặc định mọi artifact trong workspace đều bắt buộc thuộc một release package.
- Không có một màn `Kiểm tra hồ sơ` riêng; màn phát hành chỉ tổng hợp readiness cần thiết cho release package.
- Primary publish action không khả dụng khi package đang chọn còn Blocking.

## 5. Preview và xác nhận

Trước khi phát hành, user phải xem được danh sách tài liệu/phiên bản sẽ thuộc package. Bước xác nhận phải làm rõ đây là thao tác tạo bản phát hành chính thức và khóa đúng trạng thái artifact đã chọn.

Không có `Xuất PDF` trong baseline này.

## 6. Freeze / lineage authority

Khi user explicit `Phát hành bộ tài liệu`, VALORA phải freeze release manifest gồm tối thiểu:

```text
Release ID / số lần phát hành
→ danh sách artifact đã chọn
→ Document Revision tương ứng
→ Data Snapshot tương ứng nếu artifact được VALORA quản lý dữ liệu
→ Microsoft 365 file/version tương ứng
→ thời điểm phát hành
→ người thao tác
```

Revision/artifact state đã phát hành không được silent mutate. Nếu cần chỉnh sửa sau phát hành, tạo revision/version mới rồi phát hành package mới; release cũ vẫn truy vết được.

Document Revision và Microsoft 365 file version vẫn là hai lớp lineage liên kết nhưng không đồng nhất.

## 7. Lịch sử phát hành

Lịch sử tối thiểu hiển thị:

```text
Mã/lần phát hành | thời điểm | người phát hành |
số tài liệu | revision/package reference | trạng thái
```

Cho phép xem chi tiết package đã phát hành nhưng không dùng lịch sử như đường vòng để sửa release cũ.

## 8. Guardrails

- Không silent publish.
- Không silent lock trước thao tác xác nhận cuối của user.
- Không silent mutate release đã phát hành.
- Không tự thêm tài liệu vào package ngoài selection/authority.
- Không tự bỏ tài liệu có Blocking mà giả vờ package đầy đủ; phải hiển thị rõ selection và readiness.
- Không tạo KSCL/phê duyệt nhiều cấp mới.
- Không xây fake Word editor.
- Không đổi nội dung Word/narrative tại bước publish.
- Không phơi thuật ngữ kỹ thuật lineage làm mental model chính.
- Mỗi bước có một primary CTA nổi bật.

## 9. Visual authority

Mockup `Phát hành bộ tài liệu — Iteration 1` được người dùng explicit nâng thành Baseline ngày 31/08/2026. Visual authority là mockup Fluent 2 với stepper 4 bước, bảng 6 tài liệu minh họa, readiness summary, lịch sử phát hành và publish CTA bị khóa khi còn tài liệu cần cập nhật.

Dữ liệu minh họa trong mockup chỉ là placeholder thiết kế, không phải business fixture hay dữ liệu hồ sơ thật.

## 10. Boundary / ADR

Đây là UI/UX Design Authority; không đồng nghĩa product code đã implement. Không cần ADR mới chỉ để chốt visual baseline.

Nếu implementation làm thay đổi release-manifest persistence, immutable release semantics, lock boundary, Microsoft 365 version binding hoặc domain contract phát hành hiện có, cần đánh giá ADR riêng trước khi sửa product code.
