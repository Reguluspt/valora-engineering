# VALORA UI/UX v2.3 — Managed Regions Báo cáo thẩm định giá Baseline Addendum

**Trạng thái:** `DESIGN AUTHORITY ADDENDUM`  
**Baseline:** `Managed Regions — Báo cáo thẩm định giá — Iteration 1`  
**Ngày chốt:** 30/08/2026

Addendum này ghi nhận mockup Iteration 1 đã được người dùng explicit nâng thành Baseline. Khi có xung đột trong đúng scope, authority mới hơn này thắng mô tả cũ.

## 1. Mục tiêu UX

Managed Regions phải dễ hiểu cho người dùng nghiệp vụ không rành IT. UI không lấy các khái niệm kỹ thuật như Region ID, source path, content control hay sync-policy enum làm mental model chính.

Ngôn ngữ user-facing ưu tiên:

- `Quản lý vùng dữ liệu trong Báo cáo thẩm định giá`;
- `Danh sách vùng dữ liệu`;
- `Xem trước tài liệu`;
- `So sánh dữ liệu của vùng đang chọn`;
- `Dữ liệu từ VALORA`;
- `Dữ liệu đang có trong Word`;
- `Cập nhật vào Word`;
- `Giữ nguyên trong Word`;
- `Bỏ qua vùng này`.

## 2. Layout authority

Desktop-first, Fluent 2. Màn hình gồm:

1. header + trạng thái tổng thể + CTA đồng bộ;
2. hướng dẫn ngắn 4 bước cho người dùng mới;
3. metadata tài liệu;
4. cột trái — danh sách vùng dữ liệu;
5. vùng giữa — preview Word lớn nhất;
6. cột phải — so sánh dữ liệu vùng đang chọn và cách xử lý;
7. footer — summary + lịch sử đồng bộ + lưu/thoát + CTA đồng bộ.

Preview vẫn là preview; VALORA không xây Word editor giả.

## 3. Mental model thao tác

UI hướng dẫn theo 4 bước:

```text
1. Xem danh sách vùng
→ 2. Xem nội dung hiện tại
→ 3. Xem khác biệt nếu có
→ 4. Chọn vùng cần cập nhật rồi Đồng bộ
```

Màn hình phải giải thích rõ rằng VALORA chỉ cập nhật các vùng hệ thống quản lý; nội dung người dùng tự chỉnh sửa ngoài các vùng này được giữ nguyên.

## 4. Trạng thái vùng

User-facing status:

```text
Đã đồng bộ
Cần đồng bộ
Bạn tự chỉnh trong Word
Lỗi
```

Không bắt người dùng hiểu trạng thái kỹ thuật phía sau.

Chọn một vùng trong danh sách phải focus/highlight đúng vùng tương ứng trong preview và mở comparison tương ứng bên phải.

## 5. So sánh dữ liệu

Comparison panel đặt cạnh nhau:

```text
Dữ liệu từ VALORA (Data Snapshot)
↔
Dữ liệu đang có trong Word (Document Revision)
```

Các giá trị khác nhau phải được nhấn mạnh trực quan. UI giải thích bằng ngôn ngữ đơn giản rằng dữ liệu khác biệt sẽ được cập nhật vào Word khi người dùng đồng bộ.

Không silent sync.

## 6. Hành động trên vùng

Tối thiểu hỗ trợ:

```text
Cập nhật vào Word (giữ dữ liệu mới nhất từ VALORA)
Giữ nguyên trong Word (không cập nhật)
Bỏ qua vùng này
```

`Cập nhật vào Word` chỉ cập nhật phần dữ liệu thuộc vùng hệ thống quản lý, không ghi đè nội dung ngoài vùng.

`Giữ nguyên trong Word` là quyết định không cập nhật vùng ở lần xử lý hiện tại; phải thể hiện rõ nếu khác biệt vẫn còn.

`Bỏ qua vùng này` là explicit user intent; không do AI/rule engine tự đặt.

## 7. CTA và bulk sync

Primary CTA:

```text
Đồng bộ tất cả vùng (n)
```

hoặc khi người dùng chọn một tập con:

```text
Đồng bộ các vùng đã chọn (n)
```

CTA phải cho biết số vùng sẽ được cập nhật. Không silent sync và không đồng bộ vùng `Bạn tự chỉnh trong Word` nếu user chưa explicit chọn cách xử lý phù hợp.

## 8. Guardrails

- VALORA quản lý structured data, Data Snapshot, lineage, audit và sync status.
- Microsoft Word/Microsoft 365 quản lý nội dung Word và file version.
- Không xây fake Word editor.
- Không ghi đè narrative ngoài managed regions.
- Không silent overwrite nội dung người dùng đã chỉnh trong Word.
- Sync chỉ tác động vùng được quản lý và được user xác nhận theo interaction hiện hành.
- Giữ lineage `Data Snapshot → Document Revision → Microsoft 365 file/version`.
- Tài liệu đã phát hành không silent mutate; cần tuân version lifecycle.
- `Mở trong Word` là đường chỉnh sửa nội dung Word chính thức.

## 9. Khả năng tái sử dụng

Interaction model này là baseline đầu tiên cho Báo cáo thẩm định giá. Có thể tái sử dụng cho Chứng thư thẩm định giá nhưng không tự coi Chứng thư đã có visual baseline riêng cho tới khi người dùng explicit chốt.

## 10. Visual authority

Visual authority là mockup dễ dùng hơn dành cho người không rành IT được tạo ngay trước lệnh `nâng thành Baseline`, với tiêu đề `Quản lý vùng dữ liệu trong Báo cáo thẩm định giá`.
