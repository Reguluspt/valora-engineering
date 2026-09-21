# VALORA UI/UX Handoff v2.3 — Không gian tài liệu / Microsoft 365 Integration Baseline Addendum

**Trạng thái:** `DESIGN AUTHORITY ADDENDUM`

Authority chi tiết: [`assets/VALORA_M365_DOCUMENT_WORKSPACE_BASELINE_v2.3.md`](./assets/VALORA_M365_DOCUMENT_WORKSPACE_BASELINE_v2.3.md).

Addendum này supersede mọi mô tả cũ mâu thuẫn với các quyết định dưới đây.

## 2026-09-21 provider-neutral product-surface amendment

User-facing parent surface is **`Không gian tài liệu` / `Bộ tài liệu hồ sơ`**. Microsoft 365/Word/OneDrive/SharePoint are integration surfaces/actions, not the domain workspace name. Older mockup labels remain visual evidence only where they do not conflict with this naming/IA amendment.

There is no standalone `Khóa phiên bản` workflow stage. Accepted `DocumentRevision` is immutable after explicit version acceptance; Publishing binds exact accepted revisions into a `ReleaseManifest`.

## 2026-09-21 execution-boundary amendment

The visual/review semantics in this baseline remain valid, but the historical direct-write
interpretation is amended by ADR 0043–0045 and the Unified Appraisal OS roadmap.

Current default authority:

```text
reviewed document plan / candidate
→ explicit human confirmation
→ app-owned immutable DocumentRevision N+1
→ CurrentHead CAS
→ optional create-new Working / Export copy
```

A Microsoft 365 Working file is non-authoritative. Word Save, provider notification, revalidation,
preview and conflict decisions do not create a revision. Direct replacement of an existing bound
OneDrive item is historical/blocked and may not be reintroduced without separate Product Owner
authority and independent provider-concurrency proof.

## A. Routing sau Kết quả thẩm định giá

```text
Kết quả thẩm định giá
→ Không gian tài liệu / Bộ tài liệu hồ sơ
→ Tạo và quản lý Báo cáo thẩm định giá + Chứng thư thẩm định giá
→ GeneratedDocumentCandidate → explicit Xác nhận phiên bản → DocumentRevision
→ optional Microsoft 365 Working copy → Mở/chỉnh sửa trong Word
→ Return / Auto Revalidation → DocumentChangeCandidate → Rà soát thay đổi → Human Commit
→ Phát hành bộ tài liệu
```

Không xây Word editor giả trong VALORA. Preview Word trong VALORA là preview cuộn trang liên tục.

## B. Kiến trúc tài liệu

VALORA quản lý dữ liệu, lineage, snapshot và trạng thái nghiệp vụ. Microsoft 365 quản lý file và version file.

Cấu trúc thư mục authority:

```text
01_Hồ sơ gốc
02_Tài liệu thẩm định
03_Hợp đồng
04_Báo giá nhà cung cấp
05_Pháp lý
```

Không dùng `Tài liệu kiểm tra` hoặc `Lưu trữ nội bộ` như thư mục baseline.

## C. `03_Hợp đồng`

`03_Hợp đồng` chứa các file nghiệp vụ do VALORA sinh ra trong vòng đời hợp đồng, gồm tối thiểu khi nghiệp vụ có phát sinh:

- Phiếu/Giấy yêu cầu thẩm định giá;
- Danh mục;
- Biên bản/nội dung thương thảo;
- Dự thảo hợp đồng;
- Hợp đồng thẩm định giá;
- Phụ lục hợp đồng;
- Biên bản nghiệm thu;
- Biên bản thanh lý;
- tài liệu hợp đồng khác.

Đây là lớp document làm việc/sinh bởi hệ thống, không phải nơi lưu bản scan đã ký.

## D. `05_Pháp lý`

`05_Pháp lý` chứa các bản scan/chứng từ ký/đóng dấu do khách hàng/NCC hoặc bên ngoài gửi lại, gồm:

- tài liệu khách hàng ký/đóng dấu;
- hợp đồng/biên bản đã ký;
- tài liệu pháp lý khách hàng cung cấp;
- tài liệu pháp lý tài sản/hồ sơ;
- **báo giá NCC đã ký/đóng dấu**;
- chứng từ xác nhận liên quan.

File sinh ra và file scan ký là hai artifact khác nhau nhưng phải có lineage nếu liên quan cùng nghiệp vụ.

## E. Không có checkpoint xác nhận file scan

Khi người dùng nhận file scan đã ký/đóng dấu, họ tự upload/kéo thả/chuyển file vào `05_Pháp lý`.

VALORA **không yêu cầu bước xác nhận riêng**, không bắt modal `Xác nhận đã ký`, `Ghi nhận pháp lý`, `Đã nhận bản ký`.

Hệ thống có thể tự ghi metadata/audit và gợi ý liên kết file với document/báo giá gốc, nhưng gợi ý này không phải checkpoint bắt buộc.

## F. Preview và command bar

Preview Word: **cuộn trang liên tục**.

Command bar authority:

- `Mở trong Word`;
- `Đồng bộ dữ liệu`;
- `Tạo phiên bản mới`;
- `So sánh`;
- `Khóa phiên bản`;
- `...`.

**Không có chức năng `Xuất PDF`.**

## G. Trạng thái tài liệu

```text
Bản nháp → Cần đồng bộ → Đã đồng bộ → Sẵn sàng phát hành → Đã phát hành
```

Không có `Gửi kiểm tra / Chờ kiểm tra` trong single-user workflow hiện hành.

## H. Quan hệ với các authority trước

- Baseline `Kết quả thẩm định giá` với 03 bảng immutable tiếp tục giữ nguyên.
- Baseline NCCQ và child flow `Hoàn tất 01 báo giá NCC` tiếp tục giữ nguyên.
- File báo giá Word làm việc nằm ở `04_Báo giá nhà cung cấp`; bản ký/đóng dấu có thể nằm ở `05_Pháp lý` và được lineage ngược về báo giá.
- File KSCL có thể tồn tại trong bộ hồ sơ mẫu/thực tế nhưng không tạo màn hình hay workflow KSCL riêng.

## I. Design authority

Mockup lịch sử của Microsoft 365 Document Workspace vẫn là visual evidence về bố cục/tương tác, nhưng current product naming/IA phải tuân `Không gian tài liệu` provider-neutral và Fluent 2 light authority.
