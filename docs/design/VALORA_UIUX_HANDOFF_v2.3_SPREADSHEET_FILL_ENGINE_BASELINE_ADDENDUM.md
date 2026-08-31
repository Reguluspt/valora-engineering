# VALORA UI/UX v2.3 — Bảng tính Fill Engine — Implementation Contract v1 — Baseline Addendum

**Status:** Baseline / Design Authority  
**Iteration:** 1  
**Date:** 31/08/2026  
**Scope:** Generic Template Management → Bảng tính → Fill Engine; UI/UX contract và format-specific fill semantics.  
**Visual language:** Microsoft Fluent 2, desktop-first, table/data-heavy, Vietnamese-first.

## 1. Quyết định baseline

Mockup `Bảng tính Fill Engine — Implementation Contract v1.0` được nâng thành **Baseline / Design Authority**.

Baseline này khóa interaction model, layout và safety semantics của Fill Engine. Đây không đồng nghĩa product code đã implement. Nếu implementation thay đổi persistence, transaction boundary, formula/fill semantics hoặc version binding thì phải đánh giá ADR riêng.

## 2. Mental flow

```text
Chuẩn bị
→ Mapping
→ Preview & Validate
→ Fill & Recalculate
→ Save & Version
```

Mỗi context chỉ có một primary CTA. UI dùng thuật ngữ nghiệp vụ; không phơi internal ID, stack trace, HTTP/SQL hoặc raw engine terms cho người dùng cuối.

## 3. Layout authority — Fluent 2

Desktop shell giữ navigation VALORA hiện hành. Main workspace gồm:

- Header: tên contract, template/version, context hồ sơ và command bar.
- Stepper 5 bước: `Chuẩn bị | Mapping | Preview & Validate | Fill & Recalculate | Save & Version`.
- Cột trái: `Template & Output`, `Nguồn dữ liệu`, `Chế độ điền`, `Nguyên tắc an toàn`.
- Cột giữa: `Mapping Panel`, cấu hình `Repeating Rows`.
- Vùng lớn bên phải: `Preview Spreadsheet`, ưu tiên diện tích viewport.
- Hàng dưới: `Validator`, `Fill Manifest`, `Output & Lineage`.
- Footer: back/secondary action + đúng một primary CTA theo bước hiện hành.

Preview là spreadsheet preview phục vụ kiểm tra fill; không phải một Excel editor thay thế Microsoft Excel.

## 4. Logical architecture

```text
Data Sources
→ Mapping Engine
→ Fill Engine Core
→ Excel Processor
→ Validator
→ Output & Lineage
```

UI/UX authority không bắt buộc implementation dùng đúng class/module name trên. Đây là logical contract giữa dữ liệu, mapping, fill, validation và artifact lineage.

## 5. Mapping contract

Mapping hỗ trợ tối thiểu:

- thông tin hồ sơ;
- thông tin tài sản;
- vùng/cột dữ liệu;
- vùng lặp/repeating rows;
- vùng tổng hợp;
- vị trí công thức có sẵn;
- ghi chú/thuyết minh khi template có mapping tương ứng.

User phải thấy mapping theo ngôn ngữ nghiệp vụ và được quyền thêm/chỉnh mapping thủ công. AI có thể gợi ý nhưng không silent accept.

## 6. Repeating-row contract

Repeating-row setup phải mô tả rõ:

- vùng lặp trên sheet;
- dòng tiêu đề;
- dòng dữ liệu bắt đầu;
- anchor/nhận diện dòng trống hoặc vùng kết thúc;
- chính sách mở rộng vùng lặp.

Khi nhân dòng, engine phải giữ relative references theo template authority và không renumber STT nghiệp vụ nếu STT thuộc lineage gốc.

## 7. Formula authority

Reference authority `Bang Tinh - HĐ 42.xlsx`:

```text
Hn = MIN(En:Gn)
In = Dn*Hn
```

Fill Engine phải:

- giữ formula, không staticize;
- không đổi business formula thành công thức khác;
- giữ relative reference khi nhân dòng;
- cập nhật vùng `Tổng cộng` / `Làm tròn` theo cấu trúc template;
- cảnh báo trước khi chạy nếu không thể bảo toàn formula semantics.

## 8. Workbook feature preservation

Engine phải bảo toàn trong phạm vi template sử dụng:

- merge;
- style;
- border;
- number format;
- ảnh/chứng cứ;
- print/page layout;
- named range;
- data validation;
- conditional formatting;
- workbook features liên quan.

Không silent drop feature. Feature không thể bảo toàn phải tạo Warning hoặc Blocking theo mức ảnh hưởng trước khi tạo output chính thức.

## 9. Validator

Severity:

```text
Blocking | Warning | Info
```

- `Blocking`: dependency khiến output không thể được coi là hợp lệ/safe để fill hoặc lưu version.
- `Warning`: có rủi ro/chênh lệch nhưng user vẫn có thể tiếp tục nếu rule cho phép.
- `Info`: trạng thái/ghi chú kiểm tra.

Validator phải có vị trí, thông báo nghiệp vụ và action `Xem chi tiết`/đi tới nơi xử lý. Không tạo một checkpoint kiểm tra hồ sơ mới ngoài flow Fill Engine.

## 10. Fill Manifest

Mỗi lần fill phải tạo manifest/audit tối thiểu ghi nhận:

- Template Version;
- sheet/vùng đích;
- nguồn dữ liệu/Data Snapshot hoặc dataset reference;
- thời điểm chạy;
- số dòng dữ liệu;
- số ô/vùng đã điền;
- số formula giữ nguyên/được nhân theo template semantics;
- validator result;
- checksum/output identity phù hợp implementation.

Các internal identifier có thể tồn tại trong audit nhưng không bắt buộc hiển thị ở UI chính.

## 11. Output & Lineage

```text
Template Version
→ Fill Run / Manifest
→ Output File
→ Lineage & Audit
```

Safety baseline:

- không ghi đè file mẫu;
- luôn tạo output mới;
- chỉ ghi vào vùng mapping được phép;
- giữ cấu trúc/công thức/định dạng;
- có manifest và audit cho mỗi lần fill;
- không silent drop workbook feature.

Nếu output được dùng trong Document Workspace hoặc release flow, lineage phải liên kết với Data Snapshot/Document Revision theo authority của module đó; không đồng nhất Fill Run với Document Revision hoặc Microsoft 365 file version.

## 12. Visual authority

Visual baseline là mockup Fluent 2 đã được user nâng baseline ngày 31/08/2026, tiêu đề `Fill Engine — Implementation Contract v1.0`, với `Mapping` là trạng thái minh họa đang active; các bước khác dùng cùng layout/interaction model và thay primary CTA theo context.

Mockup dùng dữ liệu minh họa/synthetic; không phải dữ liệu khách hàng/NCC/hồ sơ thật.

## 13. Boundary: UI/UX vs domain vs implementation

- **UI/UX authority:** layout, mental model, controls, validator semantics, safety communication, user decisions.
- **Domain contract:** template version, mapping semantics, formula authority, feature-preservation obligations, manifest/lineage requirements.
- **Engine implementation:** library/runtime, transaction strategy, recalculation mechanism, file persistence, checksum implementation, concurrency và error-recovery kỹ thuật.

Baseline này khóa hai lớp đầu trong phạm vi nêu trên; không tự khóa lựa chọn công nghệ triển khai.

## 14. ADR

Không phát sinh ADR chỉ vì promote visual baseline. ADR cần được đánh giá nếu implementation làm thay đổi persistence/fill semantics, overwrite policy, formula semantics, workbook feature preservation, version binding hoặc audit/lineage model.