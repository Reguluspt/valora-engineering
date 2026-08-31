# VALORA UI/UX v2.3 — Authority Index

**Status:** Canonical UI/UX reading order for v2.3  
**Consolidation:** 31/08/2026 — `Quản lý Kho tri thức — Iteration 1`.

## 1. Thứ tự đọc hiện hành
1. `VALORA_UIUX_HANDOFF_v2.3.md` — canonical master.
2. `VALORA_UIUX_HANDOFF_v2.3_KNOWLEDGE_MANAGEMENT_BASELINE_ADDENDUM.md` — **Baseline `Quản lý Kho tri thức — Iteration 1`**.
3. `VALORA_UIUX_HANDOFF_v2.3_RELEASE_CONFIRMATION_BASELINE_ADDENDUM.md` — Baseline Xác nhận phát hành.
4. `VALORA_UIUX_HANDOFF_v2.3_RELEASE_EXCEPTION_REVIEW_BASELINE_ADDENDUM.md` — Baseline Xem lại & xử lý ngoại lệ.
5. `VALORA_UIUX_HANDOFF_v2.3_RELEASE_PREPARATION_BASELINE_ADDENDUM.md` — Baseline Chuẩn bị bộ phát hành.
6. Các addendum Bulk Sync, Custom Template, Document Set, Generation/Sync, Managed Regions, Sync-Version, Fill Engine, NCC warning, Result/NCCQ hiện hành.
7. `VALORA_USER_FLOW_MINDMAP_v2.3.md` — support flow; không override master.

## 2. Knowledge Management authority
`Quản lý Kho tri thức` là workspace quản trị/review độc lập với panel `Kho tri thức` trong Workbench.

IA baseline:
```text
Tài sản chuẩn | Cần rà soát | Hồ sơ cũ | Lịch sử & nguồn gốc
```

`Tài sản chuẩn` quản lý Canonical Asset / Variant / Alias / Đặc điểm KTKT có cấu trúc / lineage. `Cần rà soát` là human-review queue. `Hồ sơ cũ` phục vụ knowledge candidates từ historical dossiers. `Lịch sử & nguồn gốc` hiển thị version/lineage.

### Structured KTKT
`Đặc điểm kinh tế - kỹ thuật` phải được quản lý dưới dạng dữ liệu có cấu trúc, không chỉ một narrative string. Thuộc tính kỹ thuật có thể thay đổi theo loại tài sản; UI không hard-code schema riêng cho TV.

### Report preview / presentation
Màn chi tiết có `Xem trước theo Báo cáo thẩm định giá`, view-only. Preview theo cấu trúc công ty:
`Tên tài sản | Đặc điểm kinh tế - kỹ thuật | Đvt | SL` và hierarchy `–` / `+`.

Structured data thuộc VALORA; cách trình bày thuộc template công ty/Microsoft 365. Fill/generation phải giữ table/column/font/indentation/bullet/line spacing/cell width/border/pagination theo template. Không fake Word editor.

### Human/AI
AI chỉ gợi ý/extract/normalize/explain; không silent activate knowledge, không overwrite raw observation, không đổi presentation authority. Direct active-knowledge injection bị cấm.

`Quản lý Kho tri thức` là supporting/horizontal module, không phải checkpoint bắt buộc trong north-star case flow.

## 3. Publishing routing authority — complete
```text
Chuẩn bị bộ phát hành
→ Xem lại & xử lý ngoại lệ
→ Xác nhận phát hành [commit boundary]
→ Release Manifest + khóa revision + audit [system consequence]
```
Không UI `Khóa phiên bản` riêng. Không `Xuất PDF`.

## 4. Release Confirmation baseline
Commit gate: Blocking=0; ngoại lệ bắt buộc đã xử lý; revision hợp lệ; release plan không stale; không unresolved version conflict; tài liệu giữ trong release đạt readiness. Thành công → Release Manifest final + lock + audit/lineage.

## 5. Guardrails
- Single-user.
- Vietnamese-first, Fluent 2, desktop-first, data-heavy/table-first.
- AI advisory; human-confirmed official decisions.
- Không silent bypass/publish/overwrite/knowledge activation.
- Không fake Word editor.
- Không export PDF.
- Historical knowledge không override v2.3 price-source authority.
- Structured KTKT = business data; report formatting = company template authority.
- Published revision/release immutable.
- Một primary CTA mỗi context.

## 6. ADR
Knowledge schema/activation/versioning, attribute grouping/order persistence, lineage, presentation mapping, Managed Region merge semantics và các Release Manifest transaction semantics cần ADR nếu implementation thay đổi persistence/architecture.
