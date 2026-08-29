# VALORA — UI/UX Handoff v2.2

**Tài liệu thiết kế quy trình làm việc của người dùng**  
**Mô hình:** Single-user Workflow  
**Trạng thái:** Baseline thiết kế sản phẩm / bàn giao UI/UX đã duyệt  
**Phạm vi:** Thẩm định giá máy móc thiết bị bằng phương pháp so sánh  
**Visual baseline:** Valora shell bám sát Fluent 2, desktop-first

> v2.2 kế thừa baseline v2.1 và cập nhật S09–S12. Workflow chính thức được rút gọn cho giai đoạn chỉ có 01 người xử lý toàn bộ hồ sơ: thông tin người thực hiện chuyển vào Cấu hình; không còn checkpoint riêng `Kiểm tra hồ sơ` và `KSCL`; validation vẫn bắt buộc nhưng hiển thị ngay tại nơi phát sinh.

## 0. Quyết định v2.2 đã duyệt

- S09 — `Chuyển sang thẩm định chính thức` đã chốt layout/form và mockup Fluent 2.
- S10 — `Tổng quan hồ sơ` là dashboard điều phối workflow chính thức, không phải form nhập liệu dài.
- S11 đổi tên thành **`Xác nhận & điều chỉnh danh mục triển khai`**, cho phép giữ nguyên, thêm mới hoặc loại bớt tài sản khỏi phạm vi hồ sơ chính thức.
- S12 — `Workbench tài sản` là bảng làm việc chính cho danh mục triển khai đã được chốt.
- `Thẩm định viên`, `Trợ lý`, `Tổ trưởng/Phụ trách` được cấu hình tại `Cấu hình → Thông tin thực hiện mặc định` và kế thừa vào hồ sơ.
- `Ngày bắt đầu dự kiến` và `Ngày kết thúc dự kiến` không nhập riêng; hệ thống dẫn xuất từ `Ngày hợp đồng` và `Ngày chứng thư`.
- Ở giai đoạn single-user hiện tại, **không có bước riêng `Kiểm tra hồ sơ` và `KSCL`**.
- **Không bỏ validation dữ liệu.** Validation chạy tại từng field/dòng/màn hình và phân thành `Blocking`, `Warning`, `Info`.
- S10 chỉ tổng hợp readiness và cung cấp `Đi tới`; không yêu cầu người dùng chạy một màn hình kiểm tra riêng.
- Thiết bị bị loại ở S11 không bị xóa khỏi Pre-case; chỉ được đánh dấu `Không đưa vào hồ sơ chính thức` và vẫn giữ lineage.
- Thiết bị thêm mới tại S11 được đánh dấu `Mới bổ sung`; sau khi chốt danh mục sẽ vào S12 ở trạng thái cần hoàn thiện/nhận diện/phân tích giá tương ứng.
- S11 **chốt phạm vi tài sản, không chốt giá**.
- S09–S12 dùng cùng Valora shell theo Fluent 2, desktop-first, một primary CTA nổi bật trên mỗi màn hình.

## 1. Product baseline

- 01 người dùng nghiệp vụ xử lý toàn bộ vòng đời.
- Chỉ thẩm định giá máy móc thiết bị.
- Chỉ dùng phương pháp so sánh.
- Công việc chính: Kho tri thức + nguồn giá Internet + Thuyết minh đơn giá.
- Không thiết kế khảo sát hiện trạng.
- AI/Kho tri thức chỉ gợi ý; mọi quyết định chính thức do người dùng xác nhận.
- Excel/Word/PDF là input/output; Workbench + database là nguồn dữ liệu làm việc chính thức.
- Không thiết kế workflow giao việc/chờ xác nhận giữa nhiều tài khoản ở giai đoạn này.

## 2. North-star user flow v2.2

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
→ S09 Chuyển sang thẩm định chính thức
→ S10 Tổng quan hồ sơ
→ S11 Xác nhận & điều chỉnh danh mục triển khai
→ S12 Workbench tài sản
→ Nguồn giá & chứng cứ
→ So sánh & xác nhận giá thẩm định chính thức
→ Hoàn tất hồ sơ
→ Báo cáo & Chứng thư
→ Phát hành
→ Lưu trữ & hình thành tri thức
```

Không có checkpoint riêng `Khai báo thông tin thực hiện`, `Kiểm tra hồ sơ`, `KSCL`.

## 3. Pre-case baseline giữ nguyên từ v2.1

Trạng thái cấp danh sách: `Mới tạo`, `Mới nhận danh mục`, `Đang phân tích`, `Sẵn sàng tạo kết quả sơ bộ`, `Đã tạo kết quả sơ bộ`, `Không tiếp tục`, `Đã chuyển thành hồ sơ`.

Không dùng `Ghi nhận đã gửi`, `Chờ khách hàng phản hồi`, `Ghi nhận phản hồi`, `Đã chấp thuận giá đề xuất`.

S08 vẫn là checkpoint tích hợp trong S02. File kết quả sơ bộ là bản sao file Excel khách hàng và bổ sung đúng 02 cột `Đơn giá đề xuất`, `Thành tiền`; file gốc không bị ghi đè; output có version/lineage.

## 4. S09 — Chuyển sang thẩm định chính thức

### 4.1 Nguyên tắc

- Pre-case phải có file kết quả sơ bộ.
- Giá đề xuất sơ bộ **không tự trở thành giá thẩm định chính thức**.
- Các trường thông tin hồ sơ ở S09 không bắt buộc phải điền hết tại thời điểm chuyển; dữ liệu thiếu hiển thị `Chưa bổ sung` và có thể hoàn thiện sau.
- Chỉ validate format/logic khi người dùng có nhập giá trị; field trống chỉ trở thành blocking khi một bước sau thực sự cần dữ liệu đó để sinh/phát hành tài liệu.

### 4.2 Chủ đầu tư & liên hệ

`Chủ đầu tư` là searchable select theo tên/MST/số điện thoại. Chọn record hiện có sẽ prefill snapshot cho hồ sơ: Chủ đầu tư, Mã số thuế, Số ĐT, Địa chỉ, Tài khoản Chủ đầu tư, Người đại diện, Chức vụ, Người liên hệ.

Sửa snapshot trong hồ sơ không tự ghi đè customer master; cập nhật master phải là thao tác riêng.

### 4.3 Thông tin hồ sơ & thẩm định

**2A — Nhận diện hồ sơ** theo thứ tự:

```text
[Tài sản thẩm định]
[Mục đích]
[Ghi chú]
```

- `Tên hồ sơ` ẩn và tự sinh từ `Tài sản thẩm định`.
- Biến thể `Tài sản thẩm định (viết thường)` là dữ liệu dẫn xuất, không hiển thị field riêng.

**2B — Mốc hồ sơ / số hiệu văn bản**:

```text
[Ngày hợp đồng]    [Số hợp đồng]    [Số QĐ]
[Ngày chứng thư]   [Số chứng thư]   [Thời điểm TĐ]
[Ngày thương thảo] [Ngày dự thảo]
```

Dữ liệu dẫn xuất/ẩn: ngày hợp đồng dạng chữ; `Ngày báo cáo = Ngày chứng thư`; ngày chứng thư dạng chữ; `Thời điểm TĐ (chân trang)` tự sinh từ `Thời điểm TĐ`.

**2C — Giá trị & phí**:

```text
[Tổng giá trị] [Giá đã bao gồm]
[Phí thẩm định]
```

**Biên bản nghiệm thu & thanh lý**:

```text
[Ngày thanh lý] [Số hóa đơn] [Ngày hóa đơn]
```

Primary CTA: `Tạo hồ sơ thẩm định chính thức`. Tạo thành công → Pre-case `Đã chuyển thành hồ sơ`, hồ sơ mới `Đang xử lý`, mở S10.

## 5. Cấu hình — Thông tin thực hiện mặc định

Đưa các thông tin ít thay đổi vào `Cấu hình → Thông tin thực hiện mặc định`:

- Thẩm định viên;
- Trợ lý;
- Tổ trưởng / Phụ trách.

Hồ sơ kế thừa các giá trị này để dùng trong biểu mẫu/truy vết; không tạo checkpoint riêng.

Không nhập `Ngày bắt đầu dự kiến` / `Ngày kết thúc dự kiến` riêng:

- Ngày bắt đầu = `Ngày hợp đồng`.
- Ngày kết thúc = `Ngày chứng thư`.

Nếu dữ liệu nguồn chưa có thì hiển thị `Chưa xác định`.

## 6. S10 — Tổng quan hồ sơ

### 6.1 Mục tiêu

S10 là dashboard điều phối hồ sơ chính thức. Người dùng mở hồ sơ phải biết ngay hồ sơ nào, đang ở checkpoint nào, còn thiếu gì, việc tiếp theo là gì và dữ liệu nào kế thừa từ Pre-case.

### 6.2 Header hồ sơ

Hiển thị compact: mã hồ sơ, tài sản thẩm định/tên hồ sơ dẫn xuất, trạng thái, Chủ đầu tư, Mục đích, Thời điểm TĐ, số thiết bị triển khai, tổng giá trị sơ bộ, nguồn Pre-case và CTA `Xem/Bổ sung thông tin hồ sơ`.

### 6.3 Việc cần làm tiếp theo

Ngay sau S09, card nổi bật nhất là **`Xác nhận & điều chỉnh danh mục triển khai`**. Danh mục đang kế thừa từ Pre-case và người dùng có thể giữ nguyên, thêm mới hoặc bỏ bớt trước khi đưa vào Workbench.

### 6.4 Workflow rút gọn

1. `Thông tin hồ sơ`;
2. `Danh mục triển khai`;
3. `Hoàn thiện tài sản`;
4. `Nguồn giá & chứng cứ`;
5. `Giá thẩm định chính thức`;
6. `Hoàn tất hồ sơ`;
7. `Báo cáo & Chứng thư`;
8. `Phát hành`.

Không có checkpoint riêng `Thông tin thực hiện`, `Kiểm tra hồ sơ`, `KSCL`.

### 6.5 Readiness / cột phải

- `Tình trạng hồ sơ`: số field đã có, danh mục triển khai, số dòng đủ nhận diện, nguồn giá, giá sơ bộ, giá chính thức, mức sẵn sàng.
- `Thông tin cần bổ sung`: checklist dữ liệu còn trống; không gọi là lỗi nếu chưa tới checkpoint cần dùng; CTA `Bổ sung thông tin hồ sơ`.
- `Người thực hiện`: read-only từ Cấu hình; link `Thay đổi trong Cấu hình`.
- `Nguồn Yêu cầu sơ bộ`: mã Pre-case, file Excel nguồn, file kết quả sơ bộ, snapshot phân tích, Kho tri thức, Nguồn giá Internet, Thuyết minh; CTA `Xem dữ liệu kế thừa`.

S10 chỉ tổng hợp validation; mọi vấn đề cụ thể phải có `Đi tới` đúng nơi sửa.

## 7. S11 — Xác nhận & điều chỉnh danh mục triển khai

### 7.1 Mục tiêu

S11 **chốt phạm vi tài sản sẽ đưa vào hồ sơ chính thức, không chốt giá**.

Người dùng có thể giữ nguyên, bỏ bớt, thêm mới, khôi phục dòng đã loại trước khi xác nhận.

### 7.2 KPI

- `Danh mục từ Pre-case`;
- `Giữ lại`;
- `Mới bổ sung`;
- `Loại khỏi hồ sơ`;
- `Tổng triển khai`.

```text
Tổng triển khai = Giữ lại + Mới bổ sung
```

Ví dụ: Pre-case 147 - Loại 5 + Mới 3 = Tổng triển khai 145.

### 7.3 Grid và thao tác

Các cột: checkbox, STT, Thiết bị, SL/ĐVT, Nguồn (`Từ Pre-case` / `Mới bổ sung`), Giá sơ bộ, Trạng thái, Ghi chú, Thao tác.

Toolbar: tìm kiếm, filter trạng thái, filter nguồn, `+ Thêm thiết bị`, `Bỏ khỏi hồ sơ` cho multi-select, `Xuất Excel` nếu cần đối chiếu.

### 7.4 Loại khỏi hồ sơ

- Không xóa dữ liệu Pre-case.
- Dòng được đánh dấu `Không đưa vào hồ sơ chính thức` / `Loại khỏi hồ sơ`.
- Giá sơ bộ, nguồn Internet, Kho tri thức, thuyết minh và lịch sử vẫn giữ để truy vết.
- Bỏ dòng đã có dữ liệu cần confirm rõ ảnh hưởng.

### 7.5 Thêm mới

- Dòng mới có badge `Mới bổ sung`.
- Không tự sao chép giá từ thiết bị khác.
- Sau khi xác nhận S11, dòng mới vào S12 để nhận diện/chuẩn hóa và đi tiếp các bước nguồn giá/giá chính thức theo readiness.

### 7.6 Lineage

Phân biệt ba lớp:

1. Danh mục Pre-case gốc — bất biến theo snapshot;
2. Danh mục đã phân tích sơ bộ — giữ nguyên lịch sử;
3. Danh mục triển khai chính thức — hình thành tại S11.

### 7.7 Validation và CTA

- Dòng mới thiếu dữ liệu cơ bản → warning tại dòng.
- Trùng thiết bị → cảnh báo khi thêm.
- Bỏ dòng đã có dữ liệu → confirm.
- Dòng mới chưa có giá → vẫn cho chốt danh mục; trạng thái `Cần phân tích` ở bước sau.
- Primary CTA: `Xác nhận danh mục triển khai` → tạo snapshot danh mục chính thức và mở S12.

## 8. S12 — Workbench tài sản

### 8.1 Mục tiêu

S12 là màn hình làm việc chính của danh mục sau S11: hoàn thiện nhận diện, chuẩn hóa tên/hãng/model/xuất xứ/thông số chính, bảo toàn dữ liệu gốc, tiếp nhận gợi ý Kho tri thức nhưng không tự áp dụng, nhìn coverage nguồn giá và giá sơ bộ kế thừa.

### 8.2 KPI

- `Tài sản tổng cộng`;
- `Đủ thông tin cơ bản`;
- `Cần bổ sung`;
- `Mới bổ sung`;
- `Cần phân tích giá`.

### 8.3 Grid

Các cột chính: checkbox, STT, Tài sản gốc, Thiết bị chuẩn hóa, Hãng, Model, Xuất xứ, Thông số chính, Trạng thái, Kho tri thức, Nguồn giá, Giá sơ bộ, Thao tác.

Ưu tiên inline edit cho field ngắn; drawer `Ngữ cảnh tài sản` dùng cho field dài và quyết định nhiều ngữ cảnh. Luôn xem `Dữ liệu gốc (Excel)` cạnh `Dữ liệu chuẩn hóa`; dữ liệu gốc không bị ghi đè.

### 8.4 Kho tri thức

Gợi ý phải hiển thị candidate, mức độ tương đồng, model/thông số giống-khác, giá lịch sử và nguồn/ngày tham chiếu khi có. Người dùng có `Dùng`, `Không dùng`, `Xem chi tiết`. AI/Kho tri thức không tự xác nhận danh tính thiết bị.

### 8.5 Trạng thái dòng

Trạng thái nghiệp vụ có thể gồm `Đủ thông tin`, `Cần bổ sung`, `Mới bổ sung`, `Cần phân tích giá`. Trạng thái Kho tri thức tách riêng như `Khớp tốt`, `Cần xác nhận`, `Chưa dùng`.

S12 có thể hiển thị summary số nguồn giá, số Thuyết minh và giá sơ bộ kế thừa để giữ context, nhưng không chốt giá chính thức tại đây.

Primary CTA cuối màn hình: `Tiếp tục sang Nguồn giá & chứng cứ`.

## 9. Validation phân tán — không có bước Kiểm tra riêng

**Không có bước `Kiểm tra hồ sơ` riêng, nhưng không bỏ validation dữ liệu.**

- `Blocking`: bắt buộc xử lý trước hành động có dependency, ví dụ chưa có giá chính thức khi hoàn tất phần giá, thiếu dữ liệu bắt buộc để sinh tài liệu, ngày tháng sai logic.
- `Warning`: cho phép tiếp tục nhưng phải chỉ rõ rủi ro/cần kiểm tra, ví dụ field hồ sơ chưa bổ sung nhưng chưa tới bước phát hành, nguồn Internet cũ/mất truy cập nhưng có snapshot lịch sử.
- `Info`: thông tin trạng thái, không cản workflow.

Mọi validation phải trả lời: **Vấn đề gì → Ảnh hưởng gì → Sửa ở đâu/thế nào**. Nếu có vị trí cụ thể, luôn có CTA `Đi tới`.

S10 chỉ tổng hợp số blocking/warning và readiness; không bắt người dùng chạy kiểm tra để hệ thống mới phát hiện lỗi đã biết.

## 10. Cụm giá trong S05

```text
Đơn giá KH dự kiến
→ Giá tham chiếu Kho tri thức
→ Giá thị trường tham khảo
→ Vận chuyển (%)
→ Đơn giá đề xuất
```

Không có `Chênh lệch`; không hiển thị `Chi phí vận chuyển` hoặc `Giá sau vận chuyển`.

```text
Đơn giá đề xuất = Giá thị trường × (1 + Vận chuyển % / 100)
```

## 11. Guardrail UX / dữ liệu

- AI/Kho tri thức không auto-accept, auto-price hoặc auto-apply.
- File Excel nguồn và raw observation phải truy lại được.
- Không ghi đè dữ liệu gốc khách hàng bằng dữ liệu chuẩn hóa.
- Staging và dữ liệu chính thức phải phân biệt.
- Giá lịch sử Kho tri thức chỉ là tham khảo.
- Nguồn Internet mất truy cập vẫn giữ lịch sử URL và đánh dấu cần kiểm tra.
- Vietnamese-first, không hiển thị HTTP/SQL/stack trace/row_version cho người dùng.
- Mỗi màn hình có một primary CTA nổi bật.
- Hành động rủi ro cao phải confirm rõ thay đổi và khả năng hoàn tác.
- S09–S12 dùng cùng Valora shell theo Fluent 2, desktop-first cho grid/workbench.

## 12. Screen inventory v2.2

| ID | Màn hình | Trạng thái / quyết định v2.2 |
|---|---|---|
| S02 | Quản lý yêu cầu sơ bộ | P0 — work queue + rà soát tích hợp + tạo/quản lý file kết quả + CTA chuyển chính thức |
| S03 | Tạo yêu cầu sơ bộ | P0 |
| S04 | Upload & Mapping Excel | P0 |
| S05 | Phân tích danh mục & Giá sơ bộ | P0 |
| S06 | Panel Kho tri thức | P0 |
| S07 | Panel Nguồn giá & Thêm nguồn | P0 |
| S08 | Rà soát & tạo file kết quả sơ bộ | Không có màn hình riêng; tích hợp S02 |
| S09 | Chuyển sang thẩm định chính thức | P0 — mockup/field layout đã duyệt |
| S10 | Tổng quan hồ sơ | P0 — workflow dashboard 8 checkpoint |
| S11 | Xác nhận & điều chỉnh danh mục triển khai | P0 — giữ/thêm/loại + lineage; chốt phạm vi, không chốt giá |
| S12 | Workbench tài sản | P0 — grid + inline edit + Asset Context Drawer + KB/evidence/price summary |
| S13 | Asset Context Drawer | P0 — raw vs normalized, specs, KB/evidence context |
| S14 | So sánh & Xác nhận giá | P0 — giá sơ bộ vs giá chính thức + rationale |
| S15 | Kiểm tra hồ sơ | **Không dùng trong workflow single-user v2.2; validation phân tán** |
| S16 | KSCL Checklist | **Không dùng trong workflow single-user v2.2** |
| S17 | Hoàn tất hồ sơ | P0 — readiness summary + confirmations + blocking issues tổng hợp |
| S18 | Báo cáo & Chứng thư | P1 — templates, preview, draft versions |
| S19 | Phát hành | P1 — confirm, lock version, export |
| S20 | Lịch sử & Lưu trữ | P1 — timeline, files, sources, prices, provenance, knowledge promotion |

## 13. Mockup baseline v2.2

- S09 — Chuyển sang thẩm định chính thức, Fluent 2.
- S10 — Tổng quan hồ sơ, workflow rút gọn 8 checkpoint.
- S11 — Xác nhận & điều chỉnh danh mục triển khai, full screen riêng.
- S12 — Workbench tài sản, full screen riêng với Asset Context Drawer.

S10 phải thể hiện header hồ sơ compact, `Việc cần làm tiếp theo`, workflow 8 checkpoint, readiness, thông tin cần bổ sung, nguồn Pre-case và người thực hiện từ Cấu hình.

S11 phải thể hiện KPI `Pre-case / Giữ lại / Mới bổ sung / Loại / Tổng triển khai`, bảng danh mục, thao tác thêm/bỏ/khôi phục, detail panel, notice rằng dòng loại không bị xóa khỏi Pre-case và primary CTA `Xác nhận danh mục triển khai`.

S12 phải thể hiện KPI readiness, grid desktop-first, raw vs normalized, trạng thái nhận diện, Kho tri thức, số nguồn giá, giá sơ bộ kế thừa, Asset Context Drawer và primary CTA sang `Nguồn giá & chứng cứ`.

## 14. Trạng thái triển khai

Đây là **thiết kế mục tiêu đã duyệt**. Chưa đồng nghĩa code sản phẩm đã implement các thay đổi v2.2.

Không được suy diễn mockup = chức năng đã có trong sản phẩm.

Các guardrail kỹ thuật hiện có trong repository vẫn có hiệu lực: tenant isolation fail-closed; staging không phải official; Apply human-confirmed; restricted Workbench fields đi qua draft/commit; AI advisory-only; source evidence phải có provenance.
