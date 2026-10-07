import type { QuotePreparation, QuoteRevision, QuoteTerms, QuoteSource, QuoteSupplier, QuoteReceipt } from "../../../../api/supplierQuotes";
import type { CaseStateResponse } from "../../../../api/caseState";
export const id = "11111111-1111-4111-8111-111111111111", revision = "22222222-2222-4222-8222-222222222222";
export const command = "33333333-3333-4333-8333-333333333333", token = "a".repeat(64);
export const terms: QuoteTerms = { quotation_number: "BG-01", quotation_number_not_issued_reason: null,
  quote_date: "2026-10-06", effective_at: "2026-10-06T00:00:00Z", expires_at: null, review_due_at: "2027-10-06T00:00:00Z",
  currency: "VND", tax: "Đã gồm", delivery: "Đã gồm", condition: "Mới", warranty: "12 tháng", payment: "Chuyển khoản",
  limitations: "Tổng hợp kiểm thử", source_locator: "Page 1", acquisition_method: "already_retained_document_reference", comparison_basis: "same_working_unit_basis" };
export const supplier: QuoteSupplier = { supplier_id: id, row_version: 2, legal_name: "Công ty A", display_name: "NCC A" };
export const source: QuoteSource = { quote_id: id, source_revision_id: id, title: "Báo giá thiết bị", document_type: "supplier_quote",
  revision_number: 1, generation: 1, sha256: token, byte_length: 50, available: true };
export const quote: QuoteRevision = { quote_id: id, revision_id: revision, revision_number: 1, predecessor_id: null, supplier_id: id,
  supplier_row_version: 2, supplier, title: source.title, registrar_id: id, confirmer_id: null, registered_at: terms.effective_at,
  confirmed_at: null, status: "draft", current_head: false, latest_revision: true, eligible: false, deficiencies: [], coverage_line_ids: [], terms,
  source: { revision_id: id, generation: 1, sha256: token, byte_length: 50 },
  items: [{ item_id: id, line_id: id, quantity: "1.00000000", unit: "cai", unit_price: "123456789012345678.12345678", source_locator: "Row 1", warning_codes: [] }] };
export const prep: QuotePreparation = { project_id: id, case_version: token, project_row_version: 4, seal_id: id,
  authoritative_set_sha256: token, membership_version: 1, price_evidence_confirmation_id: id, session_id: id,
  line_versions: [{ line_id: id, row_version: 2 }], lines: [{ line_id: id, asset_name: "Máy cắt", description: "Thông số", quantity: "1.00000000", unit: "cai" }],
  writable: true, can_register: true, coverage: [{ line_id: id, supplier_count: 0, deficient: true }], concerns: [],
  quotes: [{ quote_id: id, revision_id: revision, head_version: 2, confirmed_revision_id: null, source_generation: 1,
    supplier_id: id, supplier_row_version: 2, status: "draft", eligible: false, deficiencies: [], can_confirm: true,
    can_register_line: true, can_revise: true, can_withdraw: false, can_reject: true }], result: "INCOMPLETE", next_action: null };
export const state = { case_version: token, current_stage: "SUPPLIER_QUOTES", next_action: null,
  stages: [{ stage: "SUPPLIER_QUOTES", result: "INCOMPLETE" }],
  capabilities: [{ stage: "SUPPLIER_QUOTES", provider_key: "supplier_quotes_v1", available: true }] } as CaseStateResponse;
export const receipt = { result: { project_id: id, command_id: command, contract_version: "supplier-quote-confirmation-v1" }, historical: true } as QuoteReceipt;
