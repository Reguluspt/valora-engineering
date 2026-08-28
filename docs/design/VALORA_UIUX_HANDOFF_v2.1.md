# VALORA — UI/UX Handoff v2.1

**Tài liệu thiết kế quy trình làm việc của người dùng**  
**Mô hình:** Single-user Workflow  
**Trạng thái:** Baseline thiết kế sản phẩm / bàn giao UI/UX  
**Phạm vi:** Thẩm định giá máy móc thiết bị bằng phương pháp so sánh

> v2.1 kế thừa toàn bộ baseline v2.0 và **supersede workflow phản hồi khách hàng trong Pre-case**. Sau khi tạo file kết quả sơ bộ, Valora không thiết kế các bước/trạng thái `Ghi nhận đã gửi/trao đổi`, `Chờ khách hàng phản hồi`, `Ghi nhận phản hồi` hoặc `Đã chấp thuận giá đề xuất`. Khi khách hàng đồng ý triển khai ở ngoài hệ thống, người dùng chỉ cần bấm **`Chuyển sang thẩm định chính thức`**.

## 0. Cập nhật v2.1 đã được duyệt

- S08 vẫn là checkpoint **tích hợp trong S02 — Quản lý yêu cầu sơ bộ**, không có màn hình riêng.
- Giữ bước `Rà soát & tạo file kết quả sơ bộ`.
- File kết quả sơ bộ là bản sao của file Excel khách hàng, bổ sung đúng 02 cột: `Đơn giá đề xuất` và `Thành tiền`.
- File nguồn không bị ghi đè; output có version/lineage tới Pre-case, file nguồn, mapping snapshot và snapshot giá.
- **Không thiết kế workflow gửi/chờ phản hồi trong Valora.**
- Sau khi file kết quả sơ bộ đã được tạo, CTA chính của Pre-case là **`Chuyển sang thẩm định chính thức`**.
- Việc khách hàng đồng ý triển khai diễn ra ngoài hệ thống; Valora không yêu cầu ghi nhận một trạng thái `Đã chấp thuận` trước khi chuyển.
- `Không tiếp tục` vẫn được giữ để đóng/dừng Pre-case nhưng phải bảo toàn file, snapshot, giá đề xuất và lịch sử phân tích.

## 1. Product baseline đã chốt

- 01 người dùng nghiệp vụ xử lý toàn bộ vòng đời.
- Chỉ thẩm định giá máy móc thiết bị.
- Chỉ dùng phương pháp so sánh.
- Công việc chính: Kho tri thức + nguồn giá Internet + Thuyết minh đơn giá.
- Không thiết kế khảo sát hiện trạng.
- AI/Kho tri thức chỉ gợi ý; mọi quyết định chính thức do người dùng xác nhận.
- Excel/Word là input/output; Workbench + database là nguồn dữ liệu làm việc chính thức.

## 2. North-star user flow v2.1

```text
Trang chủ
→ Quản lý yêu cầu sơ bộ
→ Tạo yêu cầu sơ bộ
→ Upload & Mapping Excel
→ Phân tích danh mục
    → Kho tri thức
    → Nguồn giá Internet / Thuyết minh đơn giá
    → Giá thị trường tham khảo
    → Vận chuyển (%)
    → Đơn giá đề xuất
→ Quay lại Quản lý yêu cầu sơ bộ
    → Rà soát tích hợp
    → Tạo file kết quả sơ bộ
→ Chuyển sang thẩm định chính thức
→ Các bước nghiệp vụ tiếp theo
```

Không có các bước trung gian `Ghi nhận đã gửi/trao đổi → Chờ khách hàng phản hồi → Ghi nhận phản hồi`.

## 3. Trạng thái Pre-case

Trạng thái cấp danh sách:

- `Mới tạo`;
- `Mới nhận danh mục`;
- `Đang phân tích`;
- `Sẵn sàng tạo kết quả sơ bộ`;
- `Đã tạo kết quả sơ bộ`;
- `Không tiếp tục`;
- `Đã chuyển thành hồ sơ`.

Không dùng các trạng thái:

- `Ghi nhận đã gửi`;
- `Chờ khách hàng phản hồi`;
- `Ghi nhận phản hồi`;
- `Đã chấp thuận giá đề xuất`.

## 4. S02 — Quản lý yêu cầu sơ bộ

### 4.1 Mục tiêu

S02 là work queue trung tâm của toàn bộ giai đoạn Pre-case và là nơi người dùng quay về sau khi phân tích danh mục.

### 4.2 KPI / work queue

KPI có thể hiển thị:

- Tổng yêu cầu;
- Đang phân tích;
- Sẵn sàng tạo kết quả sơ bộ;
- Đã tạo kết quả sơ bộ;
- Đã chuyển thành hồ sơ.

Có thể hiển thị thêm `Không tiếp tục` trong filter/trạng thái nhưng không cần là KPI chính.

### 4.3 Row action theo trạng thái

- Đang phân tích → `Tiếp tục phân tích`.
- Đã phân tích đủ điều kiện → `Rà soát & tạo file`.
- Đã tạo file kết quả sơ bộ → `Chuyển sang thẩm định chính thức`.
- Không tiếp tục → `Xem lịch sử`.
- Đã chuyển thành hồ sơ → `Mở hồ sơ chính thức`.

### 4.4 Rà soát tích hợp

Panel/drawer bên phải trên S02 hiển thị:

- mã/tên Pre-case;
- file nguồn + sheet + version;
- Tổng thiết bị;
- Đã xác nhận;
- Có dùng Kho tri thức;
- Có nguồn Internet mới;
- Có Thuyết minh;
- Cần xử lý;
- Tổng giá trị đề xuất;
- preview một số dòng;
- `Quay lại Phân tích danh mục`;
- `Tạo file kết quả sơ bộ`;
- lịch sử file đã tạo.

Nếu `Cần xử lý > 0` thì khóa thao tác tạo file.

Sau khi file đã tạo, panel chuyển sang trạng thái quản lý output:

- file kết quả hiện hành;
- version;
- `Tải file kết quả`;
- `Xem file`;
- `Tạo lại file`;
- CTA chính: **`Chuyển sang thẩm định chính thức`**;
- CTA phụ: `Quay lại Phân tích danh mục`, `Không tiếp tục`.

## 5. Điều kiện hoàn tất một dòng

Một dòng chỉ đạt khi đồng thời:

1. thiết bị đủ nhận diện để so sánh;
2. có ít nhất một căn cứ giá người dùng chấp nhận;
3. có Giá thị trường tham khảo / giá cơ sở được xác nhận;
4. Vận chuyển (%) hợp lệ, `0%` được phép;
5. có Đơn giá đề xuất;
6. người dùng đã xác nhận dòng.

`Thuyết minh đơn giá` (`USER_PRICE_JUSTIFICATION`) được phép là căn cứ duy nhất của một dòng.

Không cho hoàn tất nếu còn dòng chưa xác định được giá. Không dùng ngoại lệ “có lý do chưa xác định” để vượt checkpoint.

## 6. File kết quả sơ bộ

### 6.1 Nguyên tắc

- Là bản sao của chính file Excel khách hàng đã cung cấp.
- Giữ nguyên sheet, cấu trúc và định dạng nguồn tối đa có thể.
- Không ghi đè file gốc.
- Tại vùng bảng danh mục đã mapping, bổ sung đúng 02 cột:
  - `Đơn giá đề xuất`;
  - `Thành tiền`.
- `Thành tiền = SL × Đơn giá đề xuất`.
- Giá trị xuất lấy từ snapshot đã rà soát.
- Output phải lưu version và lineage.

### 6.2 Versioning

Nếu giá/danh mục thay đổi sau khi đã tạo output:

- file cũ không bị ghi đè;
- quay lại S05 để sửa;
- rà soát lại;
- tạo version file kết quả mới;
- lịch sử file cũ vẫn tra cứu được.

## 7. Chuyển sang thẩm định chính thức

### 7.1 Điều kiện vào

- Pre-case đã có file kết quả sơ bộ.
- Người dùng chủ động bấm `Chuyển sang thẩm định chính thức`.
- Không yêu cầu bất kỳ trạng thái trung gian về gửi/trao đổi/phản hồi.

### 7.2 UX

Wizard/Form chuyển chính thức phải:

- prefill danh mục;
- tái sử dụng giá đề xuất sơ bộ;
- tái sử dụng Kho tri thức và nguồn Internet;
- tái sử dụng file kết quả sơ bộ;
- giữ lineage tới Pre-case và file nguồn;
- chỉ lúc này mới yêu cầu thông tin pháp nhân/hợp đồng cần thiết cho hồ sơ chính thức.

Nếu danh mục triển khai thay đổi, dòng mới/thay đổi đáng kể phải quay lại `Cần phân tích giá`; không tự áp dụng giá cũ.

## 8. Cụm giá trong S05

```text
Đơn giá KH dự kiến
→ Giá tham chiếu Kho tri thức
→ Giá thị trường tham khảo
→ Vận chuyển (%)
→ Đơn giá đề xuất
```

Không có cột `Chênh lệch`.

Không hiển thị:

- `Chi phí vận chuyển`;
- `Giá sau vận chuyển`.

Công thức:

```text
Đơn giá đề xuất = Giá thị trường × (1 + Vận chuyển % / 100)
```

## 9. Guardrail UX / dữ liệu

- AI/Kho tri thức không auto-accept, auto-price hoặc auto-apply.
- File Excel nguồn và raw observation phải truy lại được.
- Không ghi đè dữ liệu gốc khách hàng bằng dữ liệu chuẩn hóa.
- Staging và dữ liệu chính thức phải phân biệt.
- Giá lịch sử Kho tri thức chỉ là tham khảo.
- Nguồn Internet mất truy cập vẫn giữ lịch sử URL và đánh dấu cần kiểm tra.
- Vietnamese-first, không hiển thị HTTP/SQL/stack trace/row_version cho người dùng.
- Cùng shell/component language Astryx/Valora cho S02–S07 và panel tích hợp.

## 10. Screen inventory liên quan

| ID | Màn hình | Trạng thái |
|---|---|---|
| S02 | Quản lý yêu cầu sơ bộ | P0 — work queue + rà soát tích hợp + tạo/quản lý file kết quả + CTA chuyển chính thức |
| S03 | Tạo yêu cầu sơ bộ | P0 |
| S04 | Upload & Mapping Excel | P0 |
| S05 | Phân tích danh mục & Giá sơ bộ | P0 |
| S06 | Panel Kho tri thức | P0 |
| S07 | Panel Nguồn giá & Thêm nguồn | P0 |
| S08 | Rà soát & tạo file kết quả sơ bộ | **Không có màn hình riêng; tích hợp S02** |
| S09 | Chuyển sang thẩm định chính thức | P0 |

S10–S20 giữ nguyên baseline v2.0 trừ khi có quyết định mới.

## 11. Mockup baseline

Mockup 08 v2.1 phải phản ánh:

- KPI không còn `Chờ phản hồi` / `Đã chấp thuận`;
- các nhóm chính: Đang phân tích, Sẵn sàng tạo kết quả sơ bộ, Đã tạo kết quả sơ bộ, Đã chuyển hồ sơ, Không tiếp tục;
- panel `Rà soát & tạo file kết quả sơ bộ`;
- trạng thái đã tạo output có CTA chính `Chuyển sang thẩm định chính thức`.

## 12. Trạng thái triển khai

Đây là **thiết kế mục tiêu đã duyệt**. Chưa đồng nghĩa code sản phẩm đã implement các thay đổi này.

Các guardrail kỹ thuật hiện có trong repository vẫn có hiệu lực: tenant isolation fail-closed; staging không phải official; Apply human-confirmed; restricted Workbench fields đi qua draft/commit; AI advisory-only; source evidence phải có provenance.
