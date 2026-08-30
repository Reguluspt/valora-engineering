# VALORA UI/UX Handoff v2.3 — AI Template Assistant Baseline Addendum

**Trạng thái:** `DESIGN AUTHORITY ADDENDUM`  
**Baseline:** `Thiết lập mẫu tài liệu — AI phân tích & đề xuất — Iteration 1`  
**Scope:** AI-assisted template setup cho Word và Bảng tính  
**Ngày chốt:** 30/08/2026

Addendum này ghi nhận quyết định explicit mới nhất của người dùng: mockup **Thiết lập mẫu tài liệu — AI phân tích & đề xuất** được nâng thành **Baseline / Design Authority**.

Authority này bổ sung AI-assisted flow cho Generic Template Management và Generic Document Mapping. AI là lớp hỗ trợ phân tích/đề xuất/kiểm tra; người dùng luôn là người xác nhận mapping và hoàn tất Template Version.

## A. Terminology authority

Trong UI nghiệp vụ, dùng:

- `Thiết lập mẫu tài liệu` thay cho việc bắt người dùng hiểu thuật ngữ kỹ thuật `Mapping Template`;
- `Bảng tính` là tên nghiệp vụ chính thức cho nhóm file Excel theo quy định công ty;
- không dùng `Phụ lục Excel` làm domain term chính;
- `Mapping` vẫn có thể tồn tại ở domain/engineering/audit nhưng không phải mental model bắt buộc của người dùng.

## B. Flow authority

Flow thiết lập template dùng chung:

```text
1. Chọn mẫu
→ 2. AI phân tích & đề xuất
→ 3. Rà soát & chỉnh sửa
→ 4. Kiểm tra & hoàn tất
```

Áp dụng cho Word generic và Bảng tính, với analyzer/mapping semantics riêng theo format.

AI không làm mất specialized authority của template Báo giá NCC; NCC vẫn Word `.docx` only và tuân TM03/TM04.

## C. Bước 2 — AI phân tích & đề xuất

Màn hình baseline gồm:

- header `Thiết lập mẫu tài liệu — AI phân tích & đề xuất`;
- stepper 4 bước;
- card file/template đang phân tích;
- summary kết quả AI;
- preview tài liệu/workbook là vùng lớn nhất;
- panel `Đề xuất mapping của AI`;
- phân loại `Tin cậy cao`, `Cần xác nhận`, `Chưa xác định`;
- action xem chi tiết/giải thích đề xuất;
- CTA tiếp tục sang `Rà soát & chỉnh sửa`.

Không hiển thị confidence kỹ thuật kiểu `0.873` như mental model chính. UI dùng nhãn nghiệp vụ; phần trăm tổng quan có thể dùng như summary nếu cần nhưng không thay thế trạng thái xác nhận.

## D. AI capabilities authority

AI có thể:

- phân tích cấu trúc template;
- nhận diện field/vùng/bảng/dòng lặp;
- đề xuất dữ liệu VALORA tương ứng;
- nhận diện vùng có khả năng là nội dung cố định hoặc user-owned;
- giải thích vì sao đề xuất mapping;
- highlight vị trí trong preview;
- phát hiện vùng chưa thiết lập;
- chạy kiểm tra/test fill;
- phát hiện lỗi hoặc rủi ro layout/công thức;
- đề xuất cách sửa.

AI chỉ tạo đề xuất. Không có đề xuất nào trở thành authority nghiệp vụ chỉ vì confidence cao.

## E. Người dùng bổ sung trường AI bỏ sót

Đây là capability bắt buộc.

Trong bước `Rà soát & chỉnh sửa`, người dùng luôn có thể:

- `+ Thêm dữ liệu cần điền`;
- chọn dữ liệu VALORA trước rồi chọn vị trí Word/Excel;
- hoặc chọn vị trí trước rồi `Gán dữ liệu`;
- sửa mapping AI đề xuất;
- xóa/không dùng mapping AI đề xuất;
- đánh dấu vị trí là `Nội dung cố định`;
- đánh dấu vùng là `Người dùng tự chỉnh` khi phù hợp.

Nếu field đã tồn tại trong Document Data Model nhưng AI bỏ sót, user có thể mapping thủ công.

Nếu Document Data Model chưa có field phù hợp, UI có thể cho `Tạo trường tùy chỉnh`, nhưng phải phân biệt:

```text
Trường chuẩn VALORA
→ dữ liệu nghiệp vụ có cấu trúc/dùng chung

Trường tùy chỉnh của template
→ phục vụ template/context cụ thể
```

Không được silently biến custom field thành canonical business field toàn hệ thống.

## F. Validation vùng chưa thiết lập

Bước `Kiểm tra & hoàn tất` phải quét lại toàn template và hiển thị các vùng có vẻ là dữ liệu động nhưng chưa được thiết lập.

Mỗi vùng chưa thiết lập tối thiểu có các action:

```text
Gán dữ liệu
Bỏ qua có chủ đích
Đây là nội dung cố định
```

Severity giữ mô hình:

```text
Blocking
Warning
Info
```

Template chỉ được coi `hợp lệ` khi không còn Blocking.

## G. Word AI analysis

Với `.docx`, AI có thể nhận diện/gợi ý:

- field đơn;
- derived field;
- bảng;
- repeating row/region;
- đoạn narrative;
- vùng nên tự đồng bộ;
- vùng chỉ điền lần đầu;
- vùng người dùng tự chỉnh trong Word.

UX không bắt user hiểu Region ID, source path, collection path hoặc Content Control kỹ thuật.

Generic Document Mapping Iteration 2 và Generic Document Template Review vẫn là authority chi tiết cho Word mapping/review; addendum này bổ sung AI-assisted pre-analysis và user recovery khi AI bỏ sót.

## H. Bảng tính AI analysis

`Bảng tính` là terminology chính thức cho `.xlsx/.xlsm` trong scope này.

AI có thể phân tích:

- workbook/sheet;
- used range;
- header nhiều tầng;
- merged cells;
- dòng nhóm/section;
- dòng mẫu dữ liệu;
- cột dữ liệu;
- công thức;
- vùng tổng hợp;
- format số/ngày;
- ảnh/chứng cứ;
- print/page layout;
- hidden row/column/sheet;
- named range và workbook structure nếu có.

Mapping Bảng tính ưu tiên nhận diện theo vùng/cột/dòng mẫu, không bắt user map từng cell nếu cấu trúc có thể suy ra an toàn.

## I. Case authority — `Bang Tinh - HĐ 42.xlsx`

File mẫu nghiệp vụ đã được dùng để định hình Iteration 1. Các quyết định thiết kế rút ra:

- Bảng tính có thể chứa section/group, không giả định repeating table phẳng;
- E:F:G là ba vị trí giá NCC, không hard-code tên NCC cụ thể thành schema;
- H là vùng công thức Đơn giá Tổ TĐG;
- I là vùng công thức Thành tiền;
- J:K là Thông tin khảo sát;
- K có thể chứa URL/text/hồ sơ nguồn/ảnh-chứng cứ;
- template có thể chứa ảnh chứng cứ neo theo dòng/vùng;
- style/layout/merge/formula phải được bảo toàn khi fill.

### Công thức authority

Theo quyết định explicit của người dùng, công thức `MIN(E:G)` trong mẫu Bảng tính phải được giữ nguyên.

Ví dụ row-level:

```text
Hn = MIN(En:Gn)
In = Dn*Hn
```

Engine phải coi đây là **template formula**, không tự thay bằng business rule khác và không ghi đè bằng giá trị tĩnh trong quá trình fill nếu mapping không explicit yêu cầu khác.

Khi nhân dòng, relative references phải tiếp tục đúng. Tổng cộng/làm tròn phải được reposition/cập nhật an toàn khi số dòng dữ liệu thay đổi.

## J. Formula / structure guardrails cho Bảng tính

AI và fill engine không được tự ý:

- xóa/đổi công thức;
- phá merged cells;
- mất style/border/number format;
- làm mất ảnh/chứng cứ;
- phá print/page layout;
- mất named ranges/data validation/conditional formatting nếu template có;
- làm mất macro trong `.xlsm` nếu format này được hỗ trợ;
- silent drop workbook features không hỗ trợ.

Nếu không bảo toàn được thành phần template, validation phải báo trước.

## K. AI guardrails

AI KHÔNG được tự:

- đổi cấu trúc biểu mẫu công ty;
- thêm/bớt/đổi thứ tự cột chính thức;
- xóa merge;
- đổi công thức `MIN(E:G)`;
- thay template formula bằng business rule khác;
- sửa narrative Word như quyết định chính thức;
- publish template;
- overwrite Template Version đang được sử dụng;
- silently accept mapping;
- silently promote custom field thành canonical domain field.

AI được phép nhận diện, đề xuất, giải thích, highlight, test, phát hiện lỗi và đề xuất sửa.

## L. Versioning & audit

Khi người dùng bấm `Hoàn tất & lưu template`, hệ thống lưu tối thiểu:

- Template ID;
- Template Version;
- Mapping Definition/version;
- validation result;
- các mapping do AI đề xuất và trạng thái user-confirmed khi cần audit;
- Data Model/version liên quan nếu có;
- file template gốc/version.

Template Version đã dùng để sinh tài liệu không silent overwrite. Thay đổi cấu trúc/mapping cần versioning phù hợp.

## M. Architecture boundary

Mental model kiến trúc:

```text
                 AI Template Assistant
                         │
        ┌────────────────┴────────────────┐
        │                                 │
   Word Analyzer                    Excel Analyzer
        │                                 │
        └──────────┬──────────────────────┘
                   ↓
          Template Mapping Model
                   ↓
          Document Data Model
                   ↓
              Validation
             ↙          ↘
      Word Renderer    Excel Fill Engine
```

AI layer có thể dùng chung capability, nhưng analyzer/renderer/fill semantics tách theo format. Không đồng nhất Word paragraph với Excel cell.

## N. Scope boundary

Baseline này khóa UX/mental model/business guardrails của AI-assisted template setup. Không khóa:

- model/provider AI;
- confidence scoring formula;
- Open XML/Graph/Excel library cụ thể;
- implementation technology;
- backend API contract chi tiết.

Design Authority không đồng nghĩa product code đã implement.
