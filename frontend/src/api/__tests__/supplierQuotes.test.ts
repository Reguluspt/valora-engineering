import { beforeEach, expect, it, vi } from "vitest";
import { request } from "../client";
import { quoteCommand, quoteItemInput, fetchQuoteHistory, fetchQuoteSources, fetchQuoteSuppliers, fetchQuotePreparation,
  fetchQuoteReceipt, submitQuoteCommand, QUOTE_CONTRACTS, type QuoteIntent } from "../supplierQuotes";
import { prep, quote, supplier, source, id, revision, command, terms } from "../../components/workbench/supplier-quotes/__tests__/fixtures";
vi.mock("../client", () => ({ request: vi.fn() }));
beforeEach(() => vi.clearAllMocks());
const build = (intent: QuoteIntent) => quoteCommand(prep, intent, command, [supplier], [source], [quote]);
it("constructs one-click confirmation with exact server CAS and no checklist or domain extras", () => {
  const payload = build({ operation: "confirm", quote_id: id, revision_id: revision });
  expect(payload).toEqual({ command_id: command, contract_version: QUOTE_CONTRACTS.confirm, confirm: true,
    expected_project_row_version: 4, expected_case_version: prep.case_version, expected_seal_id: id,
    expected_authoritative_set_sha256: prep.authoritative_set_sha256, expected_membership_version: 1,
    expected_line_versions: [{ line_id: id, row_version: 2 }], expected_session_id: id, expected_price_evidence_confirmation_id: id,
    quote_id: id, expected_revision_id: revision, expected_quote_head_version: 2, supplier_id: id,
    expected_supplier_row_version: 2, expected_source_generation: 1, reason_note: null });
});
it("registers an absent retained quote with a readable selected issuer, no automatic coverage or upload", () => {
  const p = quoteCommand({ ...prep, quotes: [] }, { operation: "register", quote_id: id, supplier_id: id, source_revision_id: id,
    terms: { ...terms, leaked: "discard" } as typeof terms }, command, [supplier], [source], []);
  expect(p.expected_quote_head_version).toBe(0); expect(p.expected_revision_id).toBeNull();
  expect(p).toHaveProperty("terms.acquisition_method", "already_retained_document_reference");
  expect(p).not.toHaveProperty("items"); expect(p).not.toHaveProperty("terms.leaked");
});
it.each(["correction", "replacement", "negotiation"] as const)("strictly constructs %s successor, stripping read metadata and preserving Decimal", mode => {
  const p = build({ operation: "revise", quote_id: id, revision_id: revision, supplier_id: id, source_revision_id: id,
    terms, items: quote.items, revision_reason: mode, reason_note: "Sửa", resolves_concern_ids: [], resolution_evidence: null });
  expect(p).toHaveProperty("revision_reason", mode);
  expect(p).toHaveProperty("items", [{ line_id: id, quantity: "1.00000000", unit: "cai", unit_price: "123456789012345678.12345678", source_locator: "Row 1" }]);
  expect(JSON.stringify(p)).not.toMatch(/appraised_unit_price|AppraisedPriceDecision|NccSelection|item_id|warning_codes/);
});
it("adds one explicit line mapping without fan-out or float coercion", () => {
  const p = build({ operation: "register-line", quote_id: id, revision_id: revision, item: quote.items[0] });
  expect(p).toHaveProperty("item.unit_price", "123456789012345678.12345678"); expect(p).not.toHaveProperty("items");
  expect(() => quoteItemInput({ ...quote.items[0], unit_price: 1 as unknown as string })).toThrow("Decimal");
});
it("binds withdrawal to the exact confirmed target while CAS still references latest negotiation head", () => {
  const confirmed = { ...quote, revision_id: command, supplier_row_version: 3 };
  const p = quoteCommand(prep, { operation: "withdraw", quote_id: id, revision_id: revision, target_revision_id: command, reason_note: "Thu hồi" },
    command, [], [], [quote, confirmed]);
  expect(p).toHaveProperty("target_revision_id", command); expect(p.expected_revision_id).toBe(revision);
  expect(p.expected_supplier_row_version).toBe(3);
  expect(build({ operation: "reject", quote_id: id, revision_id: revision, reason_note: "Loại" })).toHaveProperty("reason_note", "Loại");
});
it("rejects missing supplier/source/history and obsolete head context", () => {
  expect(() => build({ operation: "confirm", quote_id: id, revision_id: command })).toThrow();
  expect(() => quoteCommand({ ...prep, quotes: [] }, { operation: "register", quote_id: id, supplier_id: id, source_revision_id: id, terms }, command, [], [], [])).toThrow();
});
it("uses bounded scoped reads and suppresses automatic mutation retries including 401 refresh", async () => {
  await fetchQuotePreparation(id); await fetchQuoteHistory(id, 50); await fetchQuoteSuppliers(id, 100); await fetchQuoteSources(id, 150); await fetchQuoteReceipt(id, command);
  expect(vi.mocked(request).mock.calls.map(c => c[0])).toEqual([
    `/api/v1/projects/${id}/supplier-quotes/preparation`, `/api/v1/projects/${id}/supplier-quotes?offset=50&limit=50`,
    `/api/v1/projects/${id}/supplier-quotes/suppliers?offset=100&limit=50`, `/api/v1/projects/${id}/supplier-quotes/sources?offset=150&limit=50`,
    `/api/v1/projects/${id}/supplier-quotes/command-receipts/${command}`]);
  const p = build({ operation: "confirm", quote_id: id, revision_id: revision }); await submitQuoteCommand(id, "confirm", p);
  expect(request).toHaveBeenLastCalledWith(`/api/v1/projects/${id}/supplier-quotes/confirm`, { method: "POST", body: JSON.stringify(p) }, true);
});
