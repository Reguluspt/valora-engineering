# VALORA UI/UX Handoff v2.3 — 03_Hợp đồng / Danh sách & tạo tài liệu

**Trạng thái:** `BASELINE / DESIGN AUTHORITY`  
**Iteration:** 1  
**Ngày duyệt:** 30/08/2026

## 1. Scope

Baseline này khóa màn hình `03_Hợp đồng — Danh sách & tạo tài liệu` trong Microsoft 365 Document Workspace.

Mục tiêu: quản lý các tài liệu nghiệp vụ do VALORA sinh trong vòng đời hợp đồng, tạo tài liệu từ template đã cấu hình, theo dõi Data Snapshot / Document Revision / Microsoft 365 file version và giữ lineage tới bản scan ký trong `05_Pháp lý` nếu có.

Không mở rộng thành Word editor trong VALORA.

## 2. IA và layout

Desktop-first, Fluent 2, table-first. Bố cục chính:

```text
Header / breadcrumb
→ Summary trạng thái tài liệu
→ Filter + bảng danh sách tài liệu
→ Preview tài liệu đang chọn
→ Panel chi tiết / thao tác
→ Lineage & phiên bản
→ Tạo nhanh từ template
```

Bảng là bề mặt nghiệp vụ chính, không cardize danh sách tài liệu.

## 3. Danh mục tài liệu 03_Hợp đồng

Tối thiểu hỗ trợ:

- Phiếu/Giấy yêu cầu thẩm định giá;
- Danh mục;
- Biên bản / Nội dung thương thảo;
- Dự thảo hợp đồng thẩm định giá;
- Hợp đồng thẩm định giá;
- Phụ lục hợp đồng;
- Biên bản nghiệm thu;
- Biên bản thanh lý;
- tài liệu hợp đồng khác.

Bản scan đã ký/đóng dấu không bị biến thành working document trong thư mục này; artifact scan thuộc `05_Pháp lý` và được lineage ngược về tài liệu gốc khi liên quan.

## 4. Bảng danh sách

Các cột nghiệp vụ chính theo baseline:

```text
STT | Tên tài liệu | Loại tài liệu | Số / Ký hiệu |
Trạng thái | Phiên bản | Cập nhật lần cuối | Tác vụ
```

Có search/filter theo tên, loại, số hợp đồng/tài liệu, trạng thái, giai đoạn, người tạo và thời gian cập nhật.

## 5. Tạo tài liệu

Primary CTA: `Tạo tài liệu`.

Tối thiểu hỗ trợ:

- tạo từ template đã cấu hình;
- tạo bản nháp trống khi loại tài liệu cho phép;
- tải lên tài liệu Word đã có;
- tạo hàng loạt khi nghiệp vụ cần sinh nhiều tài liệu.

`Tạo nhanh từ template` có thể hiển thị các template phù hợp với context hồ sơ.

Template/version đang sử dụng phải được ghi lineage; không silent overwrite template/version đã dùng.

## 6. Preview và chỉnh sửa

Preview trong VALORA chỉ để xem, không phải Word editor.

Thao tác chỉnh sửa nội dung Word dùng `Mở trong Word` theo authority Microsoft 365 Document Workspace.

Panel chi tiết tối thiểu hiển thị loại tài liệu, mẫu sử dụng, phiên bản/revision, người tạo, thời gian tạo/cập nhật, trạng thái sync và vị trí file.

## 7. Lifecycle và trạng thái

Giữ authority:

```text
Bản nháp
→ Cần đồng bộ
→ Đã đồng bộ
→ Sẵn sàng phát hành
→ Đã phát hành
```

`Chưa tạo` có thể dùng cho entry tài liệu chưa được sinh trong danh sách/lifecycle planning; đây không thay thế lifecycle của artifact sau khi đã tạo.

Không có workflow `Gửi kiểm tra / Chờ kiểm tra` trong single-user v2.3.

## 8. Lineage / version authority

Lineage tối thiểu:

```text
Template Version
→ Data Snapshot
→ Document Revision
→ Microsoft 365 file / file version
→ Bản scan ký ở 05_Pháp lý (nếu có)
```

Phân biệt rõ:

- Template Version;
- VALORA Data Snapshot;
- Document Revision;
- Microsoft 365 file version;
- signed scan artifact.

Tạo phiên bản mới không được silent mutate revision đã phát hành.

## 9. Sync guardrail

VALORA quản lý structured business data, Data Snapshot, lineage, audit và sync status; Microsoft 365 quản lý file và trải nghiệm chỉnh sửa Word.

Nếu dữ liệu VALORA thay đổi, document có thể chuyển `Cần đồng bộ`; thao tác đồng bộ chỉ cập nhật managed regions theo authority liên quan, không overwrite narrative do người dùng chỉnh trong Word.

## 10. Visual authority

Mockup `03_Hợp đồng — Danh sách & tạo tài liệu — Iteration 1` được người dùng explicit nâng thành Baseline ngày 30/08/2026.

Visual guardrails:

- Fluent 2;
- desktop-first;
- table-first;
- viewport ưu tiên bảng + preview;
- panel phải phục vụ chi tiết/lineage, không chiếm thay diện tích bảng không cần thiết;
- Vietnamese-first.

## 11. Scope respected

Baseline này không thay đổi:

- Price & Evidence authority;
- NCCQ;
- 03 bảng Kết quả thẩm định giá immutable;
- Template Assistant authority;
- AI-TPL-4;
- M365 boundary VALORA vs Word;
- quy tắc `05_Pháp lý` cho bản scan ký.

Không sửa product code. Không phát sinh ADR kỹ thuật chỉ vì nâng visual baseline này.
