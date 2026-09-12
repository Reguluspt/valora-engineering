# VALORA — Microsoft 365 Document Workspace / Bộ tài liệu phát hành — Baseline Authority v2.3

**Trạng thái:** `BASELINE ĐÃ DUYỆT / DESIGN AUTHORITY`

## 1. Vai trò

`Microsoft 365 Document Workspace / Bộ tài liệu phát hành` là bề mặt quản lý tài liệu cuối của hồ sơ sau khi `Kết quả thẩm định giá` đã được khóa.

Nguyên tắc kiến trúc:

- `VALORA` quản lý dữ liệu nghiệp vụ, Data Snapshot, lineage, trạng thái đồng bộ và audit.
- `Microsoft 365` (OneDrive/SharePoint + Word) quản lý file, phiên bản file và trải nghiệm chỉnh sửa tài liệu.
- Không xây Word editor giả trong VALORA.
- Preview Word trong VALORA là **preview dạng cuộn trang liên tục**, không phải editor.
- Không có chức năng `Xuất PDF` trong baseline này.

## 2. Cấu trúc thư mục baseline

Cây tài liệu của hồ sơ dùng các nhóm chính:

```text
01_Hồ sơ gốc
02_Tài liệu thẩm định
03_Hợp đồng
04_Báo giá nhà cung cấp
05_Pháp lý
```

Không dùng các thư mục `Tài liệu kiểm tra`, `Lưu trữ nội bộ` trong baseline này.

### 2.1 `01_Hồ sơ gốc`

Chứa tài liệu đầu vào/gốc của hồ sơ và các file do khách hàng cung cấp trước quá trình xử lý, theo quy tắc lưu trữ hiện hành của hồ sơ.

### 2.2 `02_Tài liệu thẩm định`

Chứa các tài liệu nghiệp vụ thẩm định do VALORA sinh hoặc quản lý, gồm tối thiểu:

- Báo cáo thẩm định giá `.docx`;
- Chứng thư thẩm định giá `.docx`;
- Bảng tính thẩm định;
- Quyết định thành lập Tổ thẩm định giá;
- Kế hoạch thẩm định giá;
- Phiếu kiểm soát chất lượng khi hồ sơ thực tế cần lưu tài liệu này.

Việc tồn tại file KSCL trong hồ sơ **không tạo ra một workflow/màn hình KSCL riêng** trong single-user workflow hiện hành.

### 2.3 `03_Hợp đồng`

Chứa các **file nghiệp vụ do VALORA sinh ra** trong vòng đời hợp đồng, chủ yếu là Word `.docx`, ví dụ:

- Phiếu/Giấy yêu cầu thẩm định giá;
- Danh mục tài sản kèm theo;
- Biên bản/nội dung thương thảo;
- Dự thảo hợp đồng;
- Hợp đồng thẩm định giá;
- Phụ lục hợp đồng nếu có;
- Biên bản nghiệm thu nếu có;
- Biên bản thanh lý hợp đồng;
- tài liệu phát sinh khác thuộc quan hệ hợp đồng.

`03_Hợp đồng` là nơi chứa **bản làm việc / bản do phần mềm sinh ra**, không phải nơi mặc định lưu scan đã ký.

### 2.4 `04_Báo giá nhà cung cấp`

Chứa các file báo giá làm việc trong lifecycle NCC:

- file Word báo giá được VALORA tạo từ template NCC;
- các phiên bản gửi NCC;
- các file làm việc liên quan tới báo giá trước khi trở thành chứng từ ký/đóng dấu chính thức.

### 2.5 `05_Pháp lý`

Chứa các **bản scan/chứng từ đã ký, đóng dấu hoặc tài liệu pháp lý do bên ngoài gửi lại**, bao gồm:

- file scan khách hàng đã ký/đóng dấu;
- hợp đồng đã ký;
- biên bản thương thảo/biên bản nghiệm thu/biên bản thanh lý đã ký;
- tài liệu pháp lý khách hàng cung cấp;
- tài liệu pháp lý liên quan tới tài sản/hồ sơ;
- **báo giá NCC đã ký/đóng dấu**;
- chứng từ xác nhận khác.

Cùng một nghiệp vụ có thể tồn tại ở hai lớp:

```text
03_Hợp đồng/Hợp đồng thẩm định giá.docx
→ 05_Pháp lý/Hợp đồng thẩm định giá đã ký.pdf
```

và:

```text
04_Báo giá nhà cung cấp/Báo giá NCC A.docx
→ 05_Pháp lý/Báo giá NCC A đã ký.pdf
```

## 3. Rule file scan nhận từ khách hàng/NCC

Khi người dùng nhận file scan đã ký/đóng dấu từ khách hàng hoặc NCC:

- người dùng **tự kéo/thả, upload hoặc chuyển file vào `05_Pháp lý`**;
- **không có bước xác nhận riêng trong VALORA**;
- không có modal `Xác nhận đã ký`, `Ghi nhận pháp lý`, `Đã nhận bản ký` bắt buộc;
- thao tác quản lý file giữ gần với hành vi OneDrive/SharePoint quen thuộc.

Sau khi file nằm trong `05_Pháp lý`, VALORA có thể:

- ghi nhận metadata/version Microsoft 365;
- lưu audit;
- cho phép hoặc gợi ý liên kết file với document/báo giá gốc;
- duy trì lineage;
- dùng file pháp lý đã liên kết làm chứng cứ cho quan hệ tương ứng.

Nếu hệ thống nhận diện được file phù hợp, chỉ **gợi ý liên kết**, không tạo thêm checkpoint xác nhận bắt buộc.

## 4. Lineage tài liệu

File do VALORA sinh và file scan ký/đóng dấu là hai artifact khác nhau.

Ví dụ:

```text
Document nghiệp vụ R03
→ Word file Microsoft 365 v4.0
→ Bản scan đã ký
→ artifact pháp lý
```

Đối với báo giá NCC:

```text
NCC
→ Báo giá hiện tại
→ Dòng tài sản
→ Đơn giá NCC đã xác nhận
→ File báo giá ký/đóng dấu trong 05_Pháp lý
```

VALORA phải giữ liên kết giữa artifact pháp lý và nguồn nghiệp vụ tương ứng nhưng không buộc người dùng đi qua bước xác nhận file riêng.

## 5. Preview và Microsoft 365

Bề mặt chính gồm:

- cây thư mục hồ sơ bên trái;
- preview Word cuộn trang ở trung tâm;
- panel bên phải cho trạng thái tài liệu, Data Snapshot, Microsoft 365 version, lịch sử/lineage và thay đổi chưa đồng bộ.

Command bar baseline gồm các capability:

- `Mở trong Word`;
- `Đồng bộ dữ liệu`;
- `Tạo phiên bản mới`;
- `So sánh`;
- `Khóa phiên bản`;
- menu `...` cho thao tác phụ.

**Không có `Xuất PDF`.**

## 6. Trạng thái tài liệu

Baseline trạng thái:

```text
Bản nháp
→ Cần đồng bộ
→ Đã đồng bộ
→ Sẵn sàng phát hành
→ Đã phát hành
```

Không dùng workflow `Gửi kiểm tra / Chờ kiểm tra` trong single-user workflow hiện tại.

## 7. Đồng bộ dữ liệu

VALORA phải phân biệt:

- `VALORA Data Snapshot`;
- `Document Revision`;
- `Microsoft 365 file version`.

Khi dữ liệu nghiệp vụ thay đổi sau lần tạo/sync gần nhất, UI phải hiển thị `Cần đồng bộ` và nêu vùng bị ảnh hưởng.

Các vùng dữ liệu do VALORA quản lý có thể được cập nhật từ Data Snapshot; việc sync không được làm mất nội dung chỉnh sửa hợp lệ của người dùng ngoài các vùng managed.

## 8. Company form và output

Các biểu mẫu công ty, đặc biệt 03 bảng đã khóa trong Báo cáo thẩm định giá, tiếp tục là `immutable layout`.

Microsoft 365/Word chỉ là môi trường file/chỉnh sửa; việc tích hợp không cho phép redesign cấu trúc các biểu mẫu công ty đã chốt.

## 9. Fluent 2

Fluent Design 2 áp dụng cho:

- shell;
- navigation;
- command bar;
- tabs;
- status;
- panel metadata/sync/version;
- drawer/tooltip;
- spacing/elevation bên ngoài tài liệu.

Không dùng Fluent 2 để thay đổi form Word do công ty ban hành.

## 10. Supersession

Baseline này supersede các mockup/ý tưởng trước nếu chúng:

- có `Xuất PDF`;
- dùng preview Word kiểu phân trang từng trang thay vì cuộn trang;
- có `Tài liệu kiểm tra` hoặc `Lưu trữ nội bộ` như thư mục bắt buộc;
- thiếu `03_Hợp đồng`;
- dùng `Chứng cứ & tài liệu liên quan` thay vì `05_Pháp lý` cho scan ký/đóng dấu;
- yêu cầu người dùng xác nhận riêng khi đưa file scan ký vào hệ thống;
- coi file Word sinh ra và file scan đã ký là cùng một artifact.

Mockup được người dùng duyệt ngay trước quyết định `chốt baseline` là visual authority cho baseline này.
