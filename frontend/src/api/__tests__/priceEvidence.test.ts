import { beforeEach, expect, it, vi } from "vitest";
import { request } from "../client";
import { evidenceCommand, EVIDENCE_CONTRACTS, fetchEvidencePreparation, fetchEvidenceWorkspace, fetchEvidenceSource,
  fetchEvidenceReceipt, submitEvidence, type EvidencePreparation, type EvidenceIntent, type SourceMaterial, type RelevanceFacts } from "../priceEvidence";
vi.mock("../client", () => ({ request: vi.fn() }));
const snapshot = { project_row_version: 8, case_version: "case", seal_id: "seal", authoritative_set_sha256: "set",
  membership_version: 2, workbench_confirmation_id: "workbench", lines: [{ line_id: "one", row_version: 3, proof_sha256: "private-proof" },
    { line_id: "two", row_version: 4, proof_sha256: "second-proof" }], sources: [{ source_id: "private-source" }] } as EvidencePreparation;
const material: SourceMaterial = { category: "internet_survey", origin: "Publisher", reference: "https://example.com/evidence",
  locator: "page 1", effective_date: "2026-10-01", unknown_date_reason: null, captured_at: "2026-10-01T00:00:00Z",
  capture_method: "manual_transcription", retained_text: "Retained synthetic source text", limitations: "manual capture",
  value: { amount: "123456789012345678.12345678", range_upper: null, currency: "VND", unit_basis: "chiếc", quantity_basis: "1",
    tax: "included", delivery: "excluded", condition: "new", locator: "row 1" }, expires_at: null, explanation: null, historical: null };
const facts: RelevanceFacts = { source_portion: "portion", relevance_rationale: "relevance", suitability_rationale: "suitability",
  limitations: "limitations", applicability_date: "2026-10-01", temporal_applicability: "temporal", source_priority_rationale: "priority",
  higher_priorities_considered: [], outcome: "accepted", disposition: "qualifying_basis", review_due_at: "2026-10-10T00:00:00Z" };
const intents: EvidenceIntent[] = [
  { operation: "register", source_id: "source", predecessor_revision_id: null, material, reason_note: null },
  { operation: "decide", line_id: "one", evidence_revision_id: "revision", predecessor_relationship_id: null, prior_decision_id: null,
    expected_line_proof_sha256: "private-proof", facts, reason_note: null },
  { operation: "withdraw", target_kind: "decision", target_id: "decision", reason_note: "reason" },
  { operation: "confirm", supersedes_confirmation_id: "prior", reason_note: "reviewed" },
  { operation: "withdraw-confirmation", expected_confirmation_id: "prior", reason_note: "withdrawn" },
];
beforeEach(() => vi.clearAllMocks());
it("encodes every bounded read scope, selected line, page and audited source identity", async () => {
  await fetchEvidencePreparation("p/1"); await fetchEvidenceWorkspace("p/1", "line/2", 50);
  await fetchEvidenceSource("p/1", "revision/3"); await fetchEvidenceReceipt("p/1", "command/4");
  expect(request).toHaveBeenNthCalledWith(1, "/api/v1/projects/p%2F1/price-evidence/preparation");
  expect(request).toHaveBeenNthCalledWith(2, "/api/v1/projects/p%2F1/price-evidence/workspace?offset=50&line_id=line%2F2");
  expect(request).toHaveBeenNthCalledWith(3, "/api/v1/projects/p%2F1/price-evidence/sources/revision%2F3");
  expect(request).toHaveBeenNthCalledWith(4, "/api/v1/projects/p%2F1/price-evidence/command-receipts/command%2F4");
});
it.each(intents)("constructs the strict $operation contract with full sealed set CAS and one UUID", async intent => {
  const command = evidenceCommand(snapshot, intent, "stable-command");
  expect(command).toMatchObject({ command_id: "stable-command", contract_version: EVIDENCE_CONTRACTS[intent.operation], confirm: true,
    expected_project_row_version: 8, expected_case_version: "case", expected_seal_id: "seal", expected_authoritative_set_sha256: "set",
    expected_membership_version: 2, expected_workbench_confirmation_id: "workbench",
    expected_line_versions: [{ line_id: "one", row_version: 3 }, { line_id: "two", row_version: 4 }] });
  expect(command).not.toHaveProperty("operation"); expect(command).not.toHaveProperty("facts");
  expect(command).not.toHaveProperty("sources"); expect(command).not.toHaveProperty("appraised_unit_price");
  await submitEvidence("p", intent, snapshot, "stable-command");
  expect(request).toHaveBeenCalledExactlyOnceWith(`/api/v1/projects/p/price-evidence/${intent.operation}`,
    { method: "POST", body: JSON.stringify(command) });
});
it("keeps decimal source values as exact strings and correction as an explicit successor", () => {
  const command = evidenceCommand(snapshot, { ...intents[0], predecessor_revision_id: "prior-revision", reason_note: "Correction" } as EvidenceIntent, "command");
  expect(command).toMatchObject({ material, predecessor_revision_id: "prior-revision", reason_note: "Correction" });
  expect(JSON.parse(JSON.stringify(command)).material.value.amount).toBe("123456789012345678.12345678");
});
it("keeps human decision exact to one source revision and line without fanout", () => {
  const command = evidenceCommand(snapshot, intents[1], "command");
  expect(command).toMatchObject({ ...facts, line_id: "one", evidence_revision_id: "revision", expected_line_proof_sha256: "private-proof" });
  expect(command).not.toHaveProperty("line_ids");
});
