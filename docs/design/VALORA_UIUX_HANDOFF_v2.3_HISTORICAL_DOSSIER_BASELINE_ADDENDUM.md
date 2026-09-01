# VALORA UI/UX Handoff v2.3 — Historical Dossier Baseline Addendum

**Baseline:** `Hồ sơ cũ — Iteration 1`  
**Scope:** Knowledge Management / Historical paired-dossier bootstrap  
**Status:** Design Authority — Iteration 1  
**Visual:** Microsoft Fluent 2, desktop-first, Vietnamese-first

## 1. Vai trò
`Hồ sơ cũ` là child-view của `Quản lý Kho tri thức`, dùng để quản lý các bộ hồ sơ thẩm định giá lịch sử và tạo knowledge candidates có lineage. Đây không phải active-case workflow và không được direct-inject dữ liệu vào active knowledge.

## 2. Flow authority
```text
Nhập hồ sơ cũ
→ Phân loại tài liệu
→ Trích xuất dữ liệu
→ Ghép khớp dòng
→ Rà soát xung đột/chưa khớp
→ Tạo ứng viên tri thức
→ Cần rà soát tri thức
→ human decision
→ official/versioned knowledge khi được xác nhận
```

`Tạo ứng viên tri thức` không đồng nghĩa kích hoạt tri thức.

## 3. Dossier aggregate / source roles
UI phải bám `DossierBundle` và giữ các source file trong cùng một hồ sơ lịch sử. Tối thiểu hỗ trợ các vai trò nguồn hiện hành như customer asset list, final appraisal report, comparison table, supplier quote, catalogue, approval/QC và other evidence khi có.

Mỗi file và dữ liệu trích xuất phải giữ source identity/locator/checksum/version metadata theo authority hiện hành. Không làm mất raw source khi chuẩn hóa hoặc ghép khớp.

## 4. Layout baseline
Desktop Fluent 2:
- trái: `Danh sách hồ sơ cũ` + search/filter theo trạng thái, năm, loại tài sản;
- giữa: hồ sơ đang chọn, progress pipeline, tabs `Tổng quan | Tài liệu & tệp tin | Dữ liệu trích xuất | Ghép khớp dòng | Ứng viên đã tạo | Lịch sử xử lý`;
- phải: danh sách tài liệu nguồn, preview dữ liệu trích xuất, thông tin xử lý, ghi chú và lịch sử;
- footer/context action: hướng dẫn bước tiếp theo và primary CTA `Tạo ứng viên từ các dòng` khi đủ điều kiện.

## 5. Extraction semantics
Extraction chỉ tạo source-backed candidates. AI/rules có thể classify/extract/normalize/propose table role hoặc row alignment, nhưng không được tạo official knowledge, không sửa raw source và không tự xác nhận mapping/identity/price.

Các table role tối thiểu theo authority code-base:
- `excel_customer_asset_table`;
- `word_technical_asset_table`;
- `word_quote_comparison_table`;
- `word_final_result_table`.

## 6. Row alignment baseline
`Ghép khớp dòng` thể hiện quan hệ giữa dòng trích xuất và tri thức/tài sản liên quan. Trạng thái UI tối thiểu:
- `Đã khớp`;
- `Chưa khớp`;
- `Cần xem xét`.

Row order không phải authority duy nhất. Hệ thống phải biểu diễn được missing/inserted/split/merged/reordered/conflicting rows và yêu cầu người dùng xem xét khi không chắc chắn.

Các tín hiệu ghép khớp có thể gồm STT/section, source order, tên raw/normalized, đơn vị, số lượng, model/thuộc tính kỹ thuật, table role và precedent. Confidence chỉ hỗ trợ review, không auto-confirm.

## 7. Candidate creation
Primary CTA `Tạo ứng viên từ các dòng` chỉ tạo candidate từ tập dòng đã đủ điều kiện hoặc đã được user chọn theo rule. Sau khi tạo, candidate đi vào `Cần rà soát tri thức`.

Không có đường tắt từ `Hồ sơ cũ` sang active knowledge. Không silent overwrite canonical asset/variant/alias/KTKT.

## 8. Price/evidence boundary
Dữ liệu giá trong hồ sơ cũ phải giữ đúng semantics nguồn:
- giá khách hàng/working price = source observation;
- supplier price = quote observation/candidate;
- appraiser proposal = proposal observation;
- final result = appraised-price decision candidate sau review.

Historical knowledge chỉ hỗ trợ/tra cứu và không override price-source authority v2.3: `Giá khảo sát Internet → Thuyết minh đơn giá → Giá trong Kết quả thẩm định giá hồ sơ cũ`.

## 9. Human/AI boundary
AI/rules được phép classify/extract/align/rank/explain/suggest. Chỉ human-confirmed decision mới kích hoạt tri thức chính thức. Không auto-approve dù confidence cao. Reject/defer không xóa provenance.

## 10. Audit / lineage
Phải truy vết được tối thiểu:
`Dossier → source file → table/page/sheet/row/cell locator → extracted row → alignment candidate/decision → knowledge candidate → review decision → knowledge version`.

Lịch sử xử lý phải giữ actor/system, thời điểm, stage, kết quả, lỗi/retry khi có.

## 11. Guardrails
- Single-user workflow.
- Không direct active-knowledge injection.
- Không fake Word/Excel editor.
- Không biến historical dossier thành active case.
- Không dùng dữ liệu lịch sử để silently override giá hiện hành.
- Một primary CTA mỗi context.

## 12. ADR trigger
Nếu implementation thay đổi DossierBundle persistence, source-role model, extraction table-role contract, DossierRowAlignment persistence/decision semantics, candidate creation transaction, reliable job/retry semantics, lineage hoặc knowledge activation/versioning thì phải đánh giá ADR trước khi sửa product code.
