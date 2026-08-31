# VALORA UI/UX v2.3 — Cảnh báo giá NCC tại Tạo & quản lý báo giá — Authority Addendum

**Status:** Current Business Rule Authority  
**Date:** 31/08/2026  
**Scope:** NCCQ — `Tạo & quản lý báo giá nhà cung cấp`.

## 1. Supersession

Quyết định này **mới hơn** mô tả trước đây về màn/checkpoint `Kiểm tra quy tắc đối chiếu giá — Iteration 1`.

- Màn `Kiểm tra quy tắc đối chiếu giá` bị bỏ.
- Mockup của màn này là discarded, không phải baseline.
- Không tạo checkpoint/màn riêng để kiểm tra rule giá NCC.

## 2. Vị trí cảnh báo

Cảnh báo xuất hiện **ngay tại bước `Tạo & quản lý báo giá NCC`**, theo từng dòng tài sản.

Bảng nên thể hiện tối thiểu:

```text
Đơn giá hiện hành | Giá NCC | Chênh tiền | Chênh % | Cảnh báo
```

Có thể dùng badge/tooltip/drawer để giảm độ rộng bảng nhưng thông tin chênh lệch phải truy cập được ngay tại dòng.

## 3. Rule cảnh báo

### A. Giá NCC thấp hơn Đơn giá hiện hành

```text
Giá NCC < Đơn giá hiện hành
→ luôn Warning
```

Rule này áp dụng kể cả mức chênh lệch nhỏ hơn hoặc bằng 15%.

### B. Chênh lệch tuyệt đối lớn hơn 15%

```text
|Giá NCC - Đơn giá hiện hành| / Đơn giá hiện hành > 15%
→ Warning chênh lệch lớn
```

Suy ra phía giá cao:

```text
Giá NCC > 115% × Đơn giá hiện hành
→ Warning
```

Một dòng có thể đồng thời thỏa nhiều nguyên nhân cảnh báo; UI có thể hợp nhất presentation nhưng audit/rule result phải giữ được nguyên nhân.

## 4. Severity và hành vi

Các cảnh báo trên là **Warning, không phải Blocking**. Người dùng vẫn có thể tiếp tục tạo/hoàn tất báo giá nếu các dependency khác cho phép.

VALORA không được:

- tự sửa Giá NCC;
- tự sửa Đơn giá hiện hành;
- tự chọn giá thay người dùng;
- tạo thêm checkpoint xác nhận giá chỉ vì có Warning.

## 5. Relationship với authority khác

Giá NCC tiếp tục không phải nguồn chính để xác định đơn giá thẩm định cuối cùng. Rule này phục vụ đối chiếu và cảnh báo tại NCCQ; không override Price & Evidence priority hoặc quyền quyết định `Đơn giá hiện hành`/`Đơn giá Kết quả thẩm định giá` của người dùng.

Các mô tả cũ chỉ cảnh báo `Giá NCC lịch sử khác Giá sơ bộ từ Pre-case` bị supersede trong phạm vi presentation/rule đối chiếu hiện hành bởi rule tại addendum này khi áp dụng `Giá NCC ↔ Đơn giá hiện hành` trong NCCQ.