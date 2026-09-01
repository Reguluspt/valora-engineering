# VALORA UI/UX v2.3 — Authority Index

**Status:** Canonical UI/UX reading order for v2.3  
**Consolidation:** 01/09/2026 — `Lịch sử & nguồn gốc — Iteration 1`.

## 1. Thứ tự đọc hiện hành
1. `VALORA_UIUX_HANDOFF_v2.3.md` — canonical master.
2. `VALORA_UIUX_HANDOFF_v2.3_KNOWLEDGE_LINEAGE_HISTORY_BASELINE_ADDENDUM.md` — **Baseline `Lịch sử & nguồn gốc — Iteration 1`**.
3. `VALORA_UIUX_HANDOFF_v2.3_HISTORICAL_DOSSIER_BASELINE_ADDENDUM.md` — Baseline `Hồ sơ cũ — Iteration 1`.
4. `VALORA_UIUX_HANDOFF_v2.3_KNOWLEDGE_REVIEW_BASELINE_ADDENDUM.md` — Baseline `Cần rà soát tri thức — Iteration 1`.
5. `VALORA_UIUX_HANDOFF_v2.3_KNOWLEDGE_MANAGEMENT_BASELINE_ADDENDUM.md` — Baseline `Quản lý Kho tri thức — Iteration 1`.
6. `VALORA_UIUX_HANDOFF_v2.3_RELEASE_CONFIRMATION_BASELINE_ADDENDUM.md` — Baseline Xác nhận phát hành.
7. `VALORA_UIUX_HANDOFF_v2.3_RELEASE_EXCEPTION_REVIEW_BASELINE_ADDENDUM.md` — Baseline Xem lại & xử lý ngoại lệ.
8. `VALORA_UIUX_HANDOFF_v2.3_RELEASE_PREPARATION_BASELINE_ADDENDUM.md` — Baseline Chuẩn bị bộ phát hành.
9. Các addendum Bulk Sync, Custom Template, Document Set, Generation/Sync, Managed Regions, Sync-Version, Fill Engine, NCC warning, Result/NCCQ hiện hành.
10. `VALORA_USER_FLOW_MINDMAP_v2.3.md` — support flow; không override master.

## 2. Knowledge Management authority
`Quản lý Kho tri thức` là supporting workspace độc lập với panel tra cứu trong Workbench.

IA:
```text
Tài sản chuẩn | Cần rà soát | Hồ sơ cũ | Lịch sử & nguồn gốc
```

Structured KTKT là business data; report presentation thuộc template công ty/Microsoft 365. Historical knowledge không override price-source authority.

### 2.1 Lịch sử & nguồn gốc — Baseline Iteration 1
`Lịch sử & nguồn gốc` là read-oriented knowledge-governance traceability surface. Nó không tạo audit/version subsystem mới mà chiếu các primitive hiện hữu như `IdentityDecisionLog`, `KnowledgeVersion`, `KnowledgeLineage`, historical dossier/source locator và review decisions.

Layout authority: filter area + history table `Thời điểm | Tài sản / Tri thức | Nội dung thay đổi | Nguồn | Quyết định | Phiên bản | Người thao tác | Trạng thái` + read-only detail drawer.

Drawer tối thiểu: `Thay đổi | Nguồn gốc | Quyết định | Phiên bản & Sử dụng`; lineage chain: `Hồ sơ / nguồn gốc → File → Vị trí dữ liệu → Dữ liệu trích xuất → Candidate → Quyết định rà soát → Knowledge Version → Tài sản chuẩn / Variant / KTKT`.

Không commit CTA, edit/delete history, restore/rollback, approve hoặc activate knowledge. Chỉ contextual deep-link như `Xem nguồn gốc đầy đủ`, `Mở hồ sơ cũ`, `Mở tài sản chuẩn`, `Xem quyết định rà soát`.

### 2.2 Hồ sơ cũ — Baseline Iteration 1
`Hồ sơ cũ` quản lý historical `DossierBundle`, source files, extraction, row alignment và candidate creation. Đây không phải active-case workflow và không được direct-inject active knowledge.

Flow:
```text
Nhập hồ sơ cũ
→ Phân loại tài liệu
→ Trích xuất dữ liệu
→ Ghép khớp dòng
→ Rà soát xung đột/chưa khớp
→ Tạo ứng viên tri thức
→ Cần rà soát tri thức
→ human decision
→ official/versioned knowledge khi xác nhận
```

Layout: dossier list bên trái; hồ sơ/progress/tabs và row-alignment table ở giữa; source files + extraction preview + processing/history bên phải. Primary CTA `Tạo ứng viên từ các dòng` chỉ tạo candidate.

Row alignment status tối thiểu: `Đã khớp | Chưa khớp | Cần xem xét`. Confidence chỉ hỗ trợ review; row order không phải authority duy nhất. Raw source/locator/lineage luôn được giữ.

AI/rules chỉ classify/extract/align/rank/explain/suggest; không auto-confirm mapping/identity/price, không activate knowledge. Candidate phải qua `Cần rà soát tri thức`.

### 2.3 Cần rà soát tri thức — Baseline Iteration 1
`Cần rà soát` là human-review queue cho identity/contextual-alias/KTKT/knowledge candidates. Candidate không trở thành official knowledge nếu chưa có explicit human decision.

Decision semantics:
`Xác nhận | Chỉnh sửa rồi xác nhận | Không phù hợp | Để xử lý sau`.

Confidence/độ ưu tiên không auto-approve; reject/defer không xóa provenance; decision phải có history/lineage/audit.

## 3. Publishing routing authority — complete
```text
Chuẩn bị bộ phát hành
→ Xem lại & xử lý ngoại lệ
→ Xác nhận phát hành [commit boundary]
→ Release Manifest + khóa revision + audit [system consequence]
```
Không UI `Khóa phiên bản` riêng. Không `Xuất PDF`.

## 4. Guardrails
- Single-user.
- Vietnamese-first, Fluent 2, desktop-first, data-heavy/table-first.
- AI advisory; human-confirmed official decisions.
- Không silent bypass/publish/overwrite/knowledge activation.
- Không auto-approve knowledge candidate.
- Không direct active-knowledge injection từ hồ sơ cũ.
- Không edit/delete history hoặc restore/rollback từ `Lịch sử & nguồn gốc`.
- Không fake Word/Excel editor.
- Không export PDF.
- Historical knowledge không override v2.3 price-source authority.
- Structured KTKT = business data; report formatting = company template authority.
- Published revision/release immutable.
- Một primary CTA mỗi context.

## 5. ADR
DossierBundle/source-role persistence, extraction/table-role contract, row-alignment lifecycle/decision semantics, candidate creation transaction/reliable jobs, knowledge review/activation/versioning, lineage, presentation mapping, Managed Region merge semantics và Release Manifest transaction semantics cần ADR nếu implementation thay đổi persistence/architecture.
