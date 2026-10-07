import { request } from "./client";
import type { CaseStateNextAction } from "./caseState";

export type QuoteResult = "NOT_AVAILABLE" | "BLOCKED" | "STALE" | "INCOMPLETE" | "COMPLETE";
export interface QuoteTerms {
  quotation_number: string | null; quotation_number_not_issued_reason: string | null; quote_date: string;
  effective_at: string; expires_at: string | null; review_due_at: string; currency: string;
  tax: string; delivery: string; condition: string; warranty: string; payment: string; limitations: string;
  source_locator: string; acquisition_method: "already_retained_document_reference";
  comparison_basis: "unassessed" | "same_working_unit_basis";
}
export interface QuoteItem { line_id: string; quantity: string; unit: string; unit_price: string; source_locator: string }
export interface QuoteLine { line_id: string; asset_name: string; description: string | null; quantity: string; unit: string | null }
export interface QuoteHead {
  quote_id: string; revision_id: string; head_version: number; confirmed_revision_id: string | null;
  source_generation: number; supplier_id: string; supplier_row_version: number | null;
  status: string; eligible: boolean; deficiencies: string[];
  can_confirm: boolean; can_register_line: boolean; can_revise: boolean; can_withdraw: boolean; can_reject: boolean;
}
export interface QuotePreparation {
  project_id: string; case_version: string; project_row_version: number; seal_id: string | null;
  authoritative_set_sha256: string | null; membership_version: number | null;
  price_evidence_confirmation_id: string | null; session_id: string | null;
  line_versions: { line_id: string; row_version: number }[]; lines: QuoteLine[];
  writable: boolean; can_register: boolean; coverage: { line_id: string; supplier_count: number; deficient: boolean }[];
  concerns: { concern_id: string; quote_id: string; revision_id: string; reason_code: string }[];
  quotes: QuoteHead[]; result: QuoteResult; next_action: CaseStateNextAction | null;
}
export interface QuoteRevision {
  quote_id: string; revision_id: string; revision_number: number; predecessor_id: string | null;
  supplier_id: string; supplier_row_version: number | null; supplier: { display_name: string | null; legal_name: string }; title: string | null;
  registrar_id: string; confirmer_id: string | null; registered_at: string; confirmed_at: string | null;
  status: string; current_head: boolean; latest_revision: boolean; eligible: boolean; deficiencies: string[];
  coverage_line_ids: string[]; terms: QuoteTerms;
  source: { revision_id: string; generation: number; sha256: string; byte_length: number };
  items: (QuoteItem & { item_id: string; warning_codes: string[] })[];
}
export interface QuoteSupplier { supplier_id: string; row_version: number; display_name: string | null; legal_name: string }
export interface QuoteSource {
  quote_id: string; source_revision_id: string; title: string; document_type: string; revision_number: number;
  generation: number; sha256: string; byte_length: number; available: boolean;
}
export interface QuotePage<T> { items: T[]; offset: number; limit: number; next_offset: number | null }
export interface QuoteHistory extends QuotePage<QuoteRevision> { case_version: string }
export interface QuoteReceipt {
  result: { command_id: string; receipt_id: string; record_id: string; project_id: string; quote_id: string;
    revision_id: string; contract_version: string; project_row_version: number; created_at: string };
  historical: boolean; replayed: boolean; current_case_version: string;
}
type QuoteTarget = { quote_id: string; revision_id: string };
type QuoteSourceInput = { quote_id: string; supplier_id: string; source_revision_id: string; terms: QuoteTerms };
export type QuoteIntent =
  | ({ operation: "register" } & QuoteSourceInput)
  | ({ operation: "register-line"; item: QuoteItem } & QuoteTarget)
  | ({ operation: "revise"; revision_reason: "correction" | "replacement" | "negotiation";
      reason_note: string; items: QuoteItem[]; resolves_concern_ids: string[]; resolution_evidence: string | null;
      revision_id: string } & QuoteSourceInput)
  | ({ operation: "confirm" } & QuoteTarget)
  | ({ operation: "withdraw"; target_revision_id: string; reason_note: string } & QuoteTarget)
  | ({ operation: "reject"; reason_note: string } & QuoteTarget);
export const QUOTE_CONTRACTS = {
  register: "supplier-quote-registration-v1", "register-line": "supplier-quote-line-registration-v1",
  revise: "supplier-quote-revision-v1", confirm: "supplier-quote-confirmation-v1",
  withdraw: "supplier-quote-withdrawal-v1", reject: "supplier-quote-rejection-v1",
} as const;
const path = (id: string) => `/api/v1/projects/${encodeURIComponent(id)}/supplier-quotes`;
export const fetchQuotePreparation = (id: string) => request<QuotePreparation>(`${path(id)}/preparation`);
export const fetchQuoteHistory = (id: string, offset = 0) => request<QuoteHistory>(`${path(id)}?offset=${offset}&limit=50`);
export const fetchQuoteSuppliers = (id: string, offset = 0) => request<QuotePage<QuoteSupplier>>(`${path(id)}/suppliers?offset=${offset}&limit=50`);
export const fetchQuoteSources = (id: string, offset = 0) => request<QuotePage<QuoteSource>>(`${path(id)}/sources?offset=${offset}&limit=50`);
export const fetchQuoteReceipt = (id: string, commandId: string) => request<QuoteReceipt>(`${path(id)}/command-receipts/${encodeURIComponent(commandId)}`);

const termsInput = (t: QuoteTerms): QuoteTerms => ({ quotation_number: t.quotation_number,
  quotation_number_not_issued_reason: t.quotation_number_not_issued_reason, quote_date: t.quote_date,
  effective_at: t.effective_at, expires_at: t.expires_at, review_due_at: t.review_due_at, currency: t.currency,
  tax: t.tax, delivery: t.delivery, condition: t.condition, warranty: t.warranty, payment: t.payment,
  limitations: t.limitations, source_locator: t.source_locator, comparison_basis: t.comparison_basis,
  acquisition_method: "already_retained_document_reference" });
export function quoteItemInput(i: QuoteItem): QuoteItem {
  if (typeof i.quantity !== "string" || typeof i.unit_price !== "string") throw new Error("Exact Decimal strings required");
  return { line_id: i.line_id, quantity: i.quantity, unit: i.unit, unit_price: i.unit_price, source_locator: i.source_locator };
}

export function quoteCommand(prep: QuotePreparation, intent: QuoteIntent, commandId: string,
  suppliers: QuoteSupplier[], sources: QuoteSource[], history: QuoteRevision[]) {
  const head = prep.quotes.find(q => q.quote_id === intent.quote_id);
  if (intent.operation === "register" ? Boolean(head) : !head || head.revision_id !== intent.revision_id) throw new Error("Quotation head changed");
  const sourceCommand = intent.operation === "register" || intent.operation === "revise";
  const target = history.find(q => q.revision_id === (intent.operation === "withdraw" ? intent.target_revision_id : head?.revision_id));
  const supplier = sourceCommand ? suppliers.find(s => s.supplier_id === intent.supplier_id) : null;
  const source = sourceCommand ? sources.find(s => s.quote_id === intent.quote_id && s.source_revision_id === intent.source_revision_id) : null;
  if (sourceCommand ? !supplier || !source || !source.available : !head || !target) throw new Error("Missing authoritative command context");
  const base = { command_id: commandId, contract_version: QUOTE_CONTRACTS[intent.operation], confirm: true,
    expected_project_row_version: prep.project_row_version, expected_case_version: prep.case_version,
    expected_seal_id: prep.seal_id, expected_authoritative_set_sha256: prep.authoritative_set_sha256,
    expected_membership_version: prep.membership_version, expected_line_versions: prep.line_versions.map(v => ({ line_id: v.line_id, row_version: v.row_version })),
    expected_session_id: prep.session_id, expected_price_evidence_confirmation_id: prep.price_evidence_confirmation_id,
    quote_id: intent.quote_id, expected_revision_id: head?.revision_id ?? null, expected_quote_head_version: head?.head_version ?? 0,
    supplier_id: sourceCommand ? supplier!.supplier_id : target!.supplier_id,
    expected_supplier_row_version: sourceCommand ? supplier!.row_version : target!.supplier_row_version,
    expected_source_generation: sourceCommand ? source!.generation : target!.source.generation,
    reason_note: "reason_note" in intent ? intent.reason_note : null };
  switch (intent.operation) {
    case "register": return { ...base, source_revision_id: intent.source_revision_id, terms: termsInput(intent.terms) };
    case "register-line": return { ...base, item: quoteItemInput(intent.item) };
    case "revise": return { ...base, source_revision_id: intent.source_revision_id, terms: termsInput(intent.terms),
      revision_reason: intent.revision_reason, items: intent.items.map(quoteItemInput), resolves_concern_ids: [...intent.resolves_concern_ids], resolution_evidence: intent.resolution_evidence };
    case "withdraw": return { ...base, target_revision_id: intent.target_revision_id };
    case "confirm": case "reject": return base;
  }
}
export const submitQuoteCommand = (id: string, operation: QuoteIntent["operation"], payload: ReturnType<typeof quoteCommand>) =>
  request<QuoteReceipt>(`${path(id)}/${operation}`, { method: "POST", body: JSON.stringify(payload) }, true);
