import { act, create } from "react-test-renderer";
import { expect, it, vi } from "vitest";
import { SourceForm } from "../SourceForm";
import { RelevanceForm } from "../RelevanceForm";
import type { SourceMaterial, EvidenceSourceView } from "../../../../api/priceEvidence";
vi.mock("@fluentui/react-components", () => ({
  Field: ({ label, children, ...props }: any) => <section data-field={label} {...props}>{children}</section>,
  Input: (props: any) => <input {...props} />, Textarea: (props: any) => <textarea {...props} />,
  Select: ({ children, ...props }: any) => <select {...props}>{children}</select>,
  Button: ({ children, ...props }: any) => <button {...props}>{children}</button>,
  Checkbox: (props: any) => <input type="checkbox" {...props} />,
}));
vi.mock("../HistoricalSourceSelector", () => ({ HistoricalSourceSelector: (props: any) => <div data-history {...props} /> }));
const value = { amount: "1000000.12345678", range_upper: null, currency: "VND", unit_basis: "chiếc", quantity_basis: "1",
  tax: "included", delivery: "excluded", condition: "new", locator: "row 1" };
const material: SourceMaterial = { category: "internet_survey", origin: "Synthetic publisher", reference: "https://example.com/source",
  locator: "page 1", effective_date: "2026-10-01", unknown_date_reason: null, captured_at: "2026-10-01T00:00:00Z",
  capture_method: "manual_transcription", retained_text: "Synthetic retained source content for form testing", limitations: "synthetic",
  value, expires_at: null, explanation: null, historical: null };
const source = { category: "internet_survey", origin: "Publisher", revision: 1, evidence_revision_id: "revision", source_id: "source",
  can_accept: true, can_reject: true, explanation_input_eligible: true, decision: null } as EvidenceSourceView;
function edit(root: ReturnType<typeof create>, label: string, next: string) {
  const field = root.root.findByProps({ "data-field": label });
  const control = field.findAll(node => ["input", "textarea", "select"].includes(String(node.type)))[0];
  act(() => control.props.onChange(null, { value: next }));
}
it.each(["internet_survey", "unit_price_explanation", "prior_appraisal_result"] as const)("serializes %s through bounded source fields and preserves exact decimals", category => {
  const save = vi.fn();
  const initial: SourceMaterial = { ...material, category, capture_method: category === "unit_price_explanation" ? "authored_explanation" : "manual_transcription",
    explanation: category === "unit_price_explanation" ? { method: "sum_of_scaled_source_values", inputs: [{ evidence_revision_id: "revision", coefficient: "1.00000000" }],
      assumptions: "same currency/unit", calculations: "value × 1", units: "chiếc", currency: "VND", proposed_basis_value: value.amount } : null,
    historical: category === "prior_appraisal_result" ? { project_id: "prior-project", line_id: "prior-line", appraisal_date: "2026-10-01",
      result_excerpt: "Synthetic retained historical appraisal result content", result_locator: "result 1", result_value: value } : null };
  let root: ReturnType<typeof create>;
  act(() => { root = create(<SourceForm projectId="project" initial={initial} sources={[source]} moreSources={false}
    onMore={vi.fn()} onSave={save} onCancel={vi.fn()} />); });
  edit(root!, "Lý do tạo phiên bản thay thế", "Explicit successor correction");
  if (category === "unit_price_explanation") {
    const options = root!.root.findByProps({ "data-field": "Nguồn đầu vào 1" }).findAllByType("option");
    expect(options.map(node => node.props.value)).toEqual(["", "revision"]);
  }
  if (category === "prior_appraisal_result") {
    expect(root!.root.findByProps({ "data-history": true }).props).toMatchObject({ selectedProject: "prior-project", selectedLine: "prior-line" });
  }
  const confirm = root!.root.findByProps({ label: "Tôi xác nhận tạo phiên bản nguồn thay thế; lịch sử được giữ nguyên" });
  act(() => confirm.props.onChange(null, { checked: true }));
  act(() => root!.root.findByType("form").props.onSubmit({ preventDefault: vi.fn() }));
  expect(save).toHaveBeenCalledExactlyOnceWith({ ...initial, captured_at: "2026-10-01T00:00:00.000Z" }, "Explicit successor correction");
  expect(save.mock.calls[0][0].value.amount).toBe("1000000.12345678");
  act(() => root!.unmount());
});
it("associates field errors and refuses malformed decimal text without calculating a price", () => {
  const save = vi.fn(); let root: ReturnType<typeof create>;
  act(() => { root = create(<SourceForm projectId="project" initial={material} sources={[]} moreSources={false}
    onMore={vi.fn()} onSave={save} onCancel={vi.fn()} />); });
  edit(root!, "Giá trị ghi nhận", "1,000,000");
  edit(root!, "Nhà xuất bản / tác giả / nguồn gốc", "a".repeat(2001));
  expect(root!.root.findByProps({ "data-field": "Nhà xuất bản / tác giả / nguồn gốc" }).props.validationState).toBe("error");
  act(() => root!.root.findByType("form").props.onSubmit({ preventDefault: vi.fn() }));
  expect(save).not.toHaveBeenCalled(); expect(root!.root.findAllByProps({ role: "alert" })).toHaveLength(1);
  act(() => root!.unmount());
});
it.each(["qualifying_basis", "excluded_alternative", "unresolved_concern"] as const)("maps explicit human %s with finite deadline and exact scope copy", disposition => {
  const save = vi.fn(); let root: ReturnType<typeof create>;
  act(() => { root = create(<RelevanceForm source={{ ...source, decision: { decision_id: "prior" } as any }} lineLabel="Selected asset"
    onSave={save} onCancel={vi.fn()} />); });
  edit(root!, "Quyết định phù hợp", disposition);
  for (const label of ["Phần nguồn liên quan", "Lý do liên quan đến tài sản đang chọn", "Lý do phù hợp làm cơ sở",
    "Hạn chế khi áp dụng", "Tính phù hợp theo thời gian", "Lý do lựa chọn thứ tự ưu tiên nguồn"]) edit(root!, label, "Explicit human facts");
  edit(root!, "Ngày áp dụng", "2026-10-01"); edit(root!, "Hạn rà soát lại (giờ địa phương)", "2026-10-10T12:00");
  edit(root!, "Lý do quyết định / thay thế quyết định trước", "Explicit successor decision");
  act(() => root!.root.findByType("form").props.onSubmit({ preventDefault: vi.fn() }));
  expect(save).toHaveBeenCalledWith(expect.objectContaining({ disposition, outcome: disposition === "qualifying_basis" ? "accepted" : "rejected",
    higher_priorities_considered: [], review_due_at: expect.stringMatching(/^2026-10-10T/) }), "Explicit successor decision");
  expect(JSON.stringify(root!.toJSON())).toContain("chỉ áp dụng cho dòng tài sản đang chọn");
  act(() => root!.unmount());
});
