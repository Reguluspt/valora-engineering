import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { create, act } from "react-test-renderer";

(globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;

import { NccSelectionPage } from "../NccSelectionPage";
import { confirmNccSelection } from "../../../api/nccSelection";
import { useResolvedProject } from "../../workbench/project-context";
import { mapConfirmError, newIdempotencyKey, useNccSelection } from "../useNccSelection";

vi.mock("../../../api/nccSelection", () => ({
  confirmNccSelection: vi.fn(),
}));

vi.mock("../../workbench/project-context", () => ({
  useResolvedProject: vi.fn(),
}));

// Exercise the REAL mapConfirmError (and real codeOf/detail.error_code
// handling) instead of mocking it away; only the data hook is stubbed.
vi.mock("../useNccSelection", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../useNccSelection")>();
  return {
    ...actual,
    useNccSelection: vi.fn(),
    newIdempotencyKey: vi.fn(() => "key-1"),
  };
});

const mockResolvedProject = vi.mocked(useResolvedProject);
const mockUseNccSelection = vi.mocked(useNccSelection);
const mockConfirm = vi.mocked(confirmNccSelection);
const mockNewKey = vi.mocked(newIdempotencyKey);

function makeCandidate(overrides: Partial<any> = {}) {
  return {
    quote_line_id: "quote-1",
    quote_batch_id: "batch-1",
    quote_batch_revision_number: 1,
    supplier_id: "supplier-1",
    supplier_name: "ABB Vietnam",
    quoted_unit_price: 850,
    currency: "USD",
    quantity: 1,
    unit_of_measure: "set",
    quote_date: null,
    evidence: { evidence_file_id: "ev-1", filename: "quote.pdf", status: "active" },
    difference_amount: -150,
    difference_percent: -15,
    warnings: ["NCC_BELOW_CURRENT_PRICE"],
    eligible: true,
    ...overrides,
  };
}

function makeCurrentSelection(overrides: Partial<any> = {}) {
  return {
    selection_id: "sel-1",
    selection_revision: 2,
    quote_line_id: "quote-1",
    quote_batch_id: "batch-1",
    quote_batch_revision_number: 1,
    supplier_id: "supplier-1",
    supplier_name: "ABB Vietnam",
    quoted_unit_price: 850,
    currency: "USD",
    quantity: 1,
    unit_of_measure: "set",
    quote_date: null,
    evidence: { evidence_file_id: "ev-1", filename: "quote.pdf", status: "active" },
    current_unit_price: 1000,
    current_unit_price_currency_id: null,
    difference_amount: -150,
    difference_percent: -15,
    warnings: [],
    acknowledged_warning_codes: [],
    confirmed_by_user_id: "user-1",
    confirmed_at: "2026-09-05T00:00:00Z",
    stale: true,
    ...overrides,
  };
}

function makeLine(overrides: Partial<any> = {}) {
  return {
    asset_line_id: "line-1",
    asset_name: "Máy phát điện ABB",
    unit_id: null,
    unit_name: null,
    quantity: 1,
    appraised_unit_price: 1000,
    appraised_currency_id: null,
    current_selection: null,
    state: "unselected",
    candidates: [makeCandidate()],
    history: [],
    ...overrides,
  };
}

function makeAggregate(asset_lines: any[] = []) {
  return {
    project_id: "p1",
    kpis: {
      total_asset_lines: asset_lines.length,
      selected: asset_lines.filter((l) => l.state === "selected").length,
      unselected: asset_lines.filter((l) => l.state === "unselected").length,
      stale: asset_lines.filter((l) => l.state === "stale").length,
      eligible_quotes: asset_lines.reduce((sum, l) => sum + l.candidates.length, 0),
    },
    asset_lines,
  };
}

beforeEach(() => {
  mockResolvedProject.mockReturnValue({
    projectId: "p1",
    displayName: "Hồ sơ",
    state: "ready",
    error: null,
    retry: vi.fn(),
  });
  mockConfirm.mockReset();
  mockNewKey.mockReset();
  mockNewKey.mockReturnValue("key-1");
});

function renderPage() {
  return create(
    React.createElement(NccSelectionPage, {
      projectRef: "hd-01",
      onNavigate: vi.fn(),
    })
  );
}

function openDrawer(root: any, lineId = "line-1") {
  const row = root.root.findByProps({ "data-asset-line-id": lineId });
  act(() => { row.props.onClick(); });
}

function switchTab(root: any, index: number) {
  const tabs = root.root.findAllByProps({ role: "tab" });
  act(() => { tabs[index].props.onClick(); });
}

describe("NccSelectionPage", () => {
  it("renders a page error when the aggregate fails to load", () => {
    mockUseNccSelection.mockReturnValue({
      aggregate: null,
      state: "PAGE_ERROR",
      error: { title: "Lỗi", message: "Không thể tải", nextAction: "Thử lại" },
      retry: vi.fn(),
      reload: vi.fn(),
    });
    let root: any;
    act(() => { root = renderPage(); });
    expect(root.root.findAllByProps({ "data-state": "PAGE_ERROR" }).length).toBeGreaterThan(0);
  });

  it("shows EMPTY_FIRST_USE when the project has no asset lines", () => {
    mockUseNccSelection.mockReturnValue({
      aggregate: makeAggregate([]),
      state: "READY",
      error: null,
      retry: vi.fn(),
      reload: vi.fn(),
    });
    let root: any;
    act(() => { root = renderPage(); });
    expect(root.root.findAllByProps({ "data-empty": "first-use" }).length).toBeGreaterThan(0);
  });

  it("shows EMPTY_NO_RESULTS when search matches nothing", () => {
    mockUseNccSelection.mockReturnValue({
      aggregate: makeAggregate([makeLine()]),
      state: "READY",
      error: null,
      retry: vi.fn(),
      reload: vi.fn(),
    });
    let root: any;
    act(() => { root = renderPage(); });
    const search = root.root.findByProps({ className: "ncc-search" });
    act(() => { search.props.onChange({ target: { value: "khong-khop" } }); });
    expect(root.root.findAllByProps({ "data-empty": "no-results" }).length).toBeGreaterThan(0);
  });

  it("renders KPI summary and the asset-line table on success", () => {
    mockUseNccSelection.mockReturnValue({
      aggregate: makeAggregate([makeLine()]),
      state: "READY",
      error: null,
      retry: vi.fn(),
      reload: vi.fn(),
    });
    let root: any;
    act(() => { root = renderPage(); });
    expect(root.root.findAllByProps({ className: "ncc-kpis" }).length).toBeGreaterThan(0);
    expect(root.root.findAllByProps({ "data-asset-line-id": "line-1" }).length).toBeGreaterThan(0);
  });

  it("confirms a candidate and reloads the aggregate", async () => {
    mockUseNccSelection.mockReturnValue({
      aggregate: makeAggregate([makeLine()]),
      state: "READY",
      error: null,
      retry: vi.fn(),
      reload: vi.fn(),
    });
    mockConfirm.mockResolvedValue({ selection_revision: 1 } as any);

    let root: any;
    await act(async () => { root = renderPage(); });

    const row = root.root.findByProps({ "data-asset-line-id": "line-1" });
    act(() => { row.props.onClick(); });

    const candidate = root.root.findByProps({ "data-candidate-id": "quote-1" });
    const radio = candidate.findAllByProps({ type: "radio" })[0];
    act(() => { radio.props.onChange(); });

    // Warning is visible before confirmation and its code is acknowledged in mockConfirm
    expect(root.root.findAllByProps({ "data-warning": "true" }).length).toBeGreaterThan(0);
    expect(root.root.findByProps({ className: "ncc-warning-summary" })).toBeDefined();

    const confirmBtn = root.root.findByProps({ "data-primary-action": "true" });
    await act(async () => { confirmBtn.props.onClick(); });

    expect(mockConfirm).toHaveBeenCalledWith("p1", "line-1", {
      quote_line_id: "quote-1",
      expected_selection_revision: 0,
      acknowledged_warning_codes: ["NCC_BELOW_CURRENT_PRICE"],
      idempotency_key: "key-1",
      confirmed: true,
    });
    expect(mockUseNccSelection).toHaveBeenCalled();
    expect(root.root.findAllByProps({ "data-state": "PARTIAL_SUCCESS" })).toHaveLength(1);
  });

  it("reuses the idempotency key when retrying the same confirmation attempt", async () => {
    mockUseNccSelection.mockReturnValue({
      aggregate: makeAggregate([makeLine()]),
      state: "READY",
      error: null,
      retry: vi.fn(),
      reload: vi.fn(),
    });
    mockNewKey.mockReturnValueOnce("key-1").mockReturnValueOnce("key-2");
    mockConfirm.mockRejectedValue({ status: 503 });

    let root: any;
    await act(async () => { root = renderPage(); });
    openDrawer(root);
    const radio = root.root
      .findByProps({ "data-candidate-id": "quote-1" })
      .findAllByProps({ type: "radio" })[0];
    act(() => { radio.props.onChange(); });

    await act(async () => { root.root.findByProps({ "data-primary-action": "true" }).props.onClick(); });
    await act(async () => { root.root.findByProps({ "data-primary-action": "true" }).props.onClick(); });

    expect(mockNewKey).toHaveBeenCalledTimes(1);
    expect(mockConfirm.mock.calls.map((call) => call[2].idempotency_key)).toEqual([
      "key-1",
      "key-1",
    ]);
  });

  it("starts a new idempotency attempt when the candidate changes", async () => {
    const candidates = [
      makeCandidate(),
      makeCandidate({ quote_line_id: "quote-2", supplier_id: "supplier-2", supplier_name: "Siemens" }),
    ];
    mockUseNccSelection.mockReturnValue({
      aggregate: makeAggregate([makeLine({ candidates })]),
      state: "READY",
      error: null,
      retry: vi.fn(),
      reload: vi.fn(),
    });
    mockNewKey.mockReturnValueOnce("key-1").mockReturnValueOnce("key-2");
    mockConfirm.mockRejectedValue({ status: 503 });

    let root: any;
    await act(async () => { root = renderPage(); });
    openDrawer(root);
    const firstRadio = root.root
      .findByProps({ "data-candidate-id": "quote-1" })
      .findAllByProps({ type: "radio" })[0];
    act(() => { firstRadio.props.onChange(); });
    await act(async () => { root.root.findByProps({ "data-primary-action": "true" }).props.onClick(); });

    const secondRadio = root.root
      .findByProps({ "data-candidate-id": "quote-2" })
      .findAllByProps({ type: "radio" })[0];
    act(() => { secondRadio.props.onChange(); });
    await act(async () => { root.root.findByProps({ "data-primary-action": "true" }).props.onClick(); });

    expect(mockConfirm.mock.calls.map((call) => [
      call[2].quote_line_id,
      call[2].idempotency_key,
    ])).toEqual([
      ["quote-1", "key-1"],
      ["quote-2", "key-2"],
    ]);
  });

  it("starts a new idempotency attempt after the drawer is closed and reopened", async () => {
    mockUseNccSelection.mockReturnValue({
      aggregate: makeAggregate([makeLine()]),
      state: "READY",
      error: null,
      retry: vi.fn(),
      reload: vi.fn(),
    });
    mockNewKey.mockReturnValueOnce("key-1").mockReturnValueOnce("key-2");
    mockConfirm.mockRejectedValue({ status: 503 });

    let root: any;
    await act(async () => { root = renderPage(); });
    openDrawer(root);
    let radio = root.root
      .findByProps({ "data-candidate-id": "quote-1" })
      .findAllByProps({ type: "radio" })[0];
    act(() => { radio.props.onChange(); });
    await act(async () => { root.root.findByProps({ "data-primary-action": "true" }).props.onClick(); });

    act(() => { root.root.findByProps({ className: "ncc-drawer-close" }).props.onClick(); });
    openDrawer(root);
    radio = root.root
      .findByProps({ "data-candidate-id": "quote-1" })
      .findAllByProps({ type: "radio" })[0];
    act(() => { radio.props.onChange(); });
    await act(async () => { root.root.findByProps({ "data-primary-action": "true" }).props.onClick(); });

    expect(mockConfirm.mock.calls.map((call) => call[2].idempotency_key)).toEqual([
      "key-1",
      "key-2",
    ]);
  });

  it("maps a real 409 detail.error_code to VERSION_CONFLICT and reloads", async () => {
    const retryFn = vi.fn();
    mockUseNccSelection.mockReturnValue({
      aggregate: makeAggregate([makeLine()]),
      state: "READY",
      error: null,
      retry: retryFn,
      reload: retryFn,
    });
    // Real backend shape: HTTPException detail carries error_code, which the
    // API client surfaces as error.detail.error_code (code stays undefined).
    mockConfirm.mockRejectedValue({
      status: 409,
      detail: { error_code: "selection_revision_conflict", detail: "revision mismatch" },
    });

    let root: any;
    await act(async () => { root = renderPage(); });

    const row = root.root.findByProps({ "data-asset-line-id": "line-1" });
    act(() => { row.props.onClick(); });
    const candidate = root.root.findByProps({ "data-candidate-id": "quote-1" });
    const radio = candidate.findAllByProps({ type: "radio" })[0];
    act(() => { radio.props.onChange(); });
    const confirmBtn = root.root.findByProps({ "data-primary-action": "true" });
    await act(async () => { confirmBtn.props.onClick(); });

    expect(root.root.findAllByProps({ "data-state": "VERSION_CONFLICT" }).length).toBeGreaterThan(0);
    expect(root.root.findByProps({ "data-primary-action": "true" }).props.disabled).toBe(true);
    expect(retryFn).toHaveBeenCalled();
  });

  it("maps a nested ApiError 409 shape to VERSION_CONFLICT and reloads", async () => {
    const retryFn = vi.fn();
    mockUseNccSelection.mockReturnValue({
      aggregate: makeAggregate([makeLine()]),
      state: "READY",
      error: null,
      retry: retryFn,
      reload: retryFn,
    });
    // ApiError shape from client.ts: ApiError.detail is the response body,
    // so the service code sits at detail.detail.error_code.
    mockConfirm.mockRejectedValue({
      status: 409,
      code: undefined,
      detail: { detail: { error_code: "selection_revision_conflict", detail: "locked" } },
    });

    let root: any;
    await act(async () => { root = renderPage(); });

    const row = root.root.findByProps({ "data-asset-line-id": "line-1" });
    act(() => { row.props.onClick(); });
    const candidate = root.root.findByProps({ "data-candidate-id": "quote-1" });
    const radio = candidate.findAllByProps({ type: "radio" })[0];
    act(() => { radio.props.onChange(); });
    const confirmBtn = root.root.findByProps({ "data-primary-action": "true" });
    await act(async () => { confirmBtn.props.onClick(); });

    expect(root.root.findAllByProps({ "data-state": "VERSION_CONFLICT" }).length).toBeGreaterThan(0);
    expect(retryFn).toHaveBeenCalled();
  });

  it("starts with no candidate selected and no confirm CTA, even for stale lines", async () => {
    const staleLine = makeLine({
      state: "stale",
      current_selection: makeCurrentSelection(),
      history: [
        { selection_revision: 1, quote_line_id: "quote-1", supplier_name: "ABB Vietnam", quoted_unit_price: 850, currency: "USD", difference_amount: -150, difference_percent: -15, warnings: [], confirmed_by_user_id: "user-1", confirmed_at: "2026-09-05T00:00:00Z" },
      ],
    });
    mockUseNccSelection.mockReturnValue({
      aggregate: makeAggregate([staleLine]),
      state: "READY",
      error: null,
      retry: vi.fn(),
      reload: vi.fn(),
    });

    let root: any;
    await act(async () => { root = renderPage(); });

    // Stale line is labeled "Cần xem lại" in the table
    const stateBadge = root.root.findByProps({ "data-state": "stale" });
    expect(stateBadge.props.children).toBe("Cần xem lại");

    openDrawer(root);

    // No silent preselect: no radio is checked and no confirm CTA is shown
    // until the user explicitly selects a candidate.
    const radios = root.root.findAllByProps({ type: "radio" });
    expect(radios.length).toBeGreaterThan(0);
    for (const radio of radios) {
      expect(radio.props.checked).toBe(false);
    }
    expect(root.root.findAllByProps({ "data-primary-action": "true" }).length).toBe(0);

    // Current selection tab also labels stale decision
    switchTab(root, 1);
    const staleNotice = root.root.findByProps({ "data-stale": "true" });
    expect(staleNotice).toBeDefined();
    const noticeTitle = staleNotice.findAll((node: any) => node.type === "strong")[0];
    expect(String(noticeTitle.props.children)).toContain("Cần xem lại");
  });

  it("reveals server-provided evidence metadata through an accessible disclosure", async () => {
    const line = makeLine({
      state: "selected",
      current_selection: makeCurrentSelection(),
    });
    mockUseNccSelection.mockReturnValue({
      aggregate: makeAggregate([line]),
      state: "READY",
      error: null,
      retry: vi.fn(),
      reload: vi.fn(),
    });

    let root: any;
    await act(async () => { root = renderPage(); });
    openDrawer(root);
    switchTab(root, 1); // current-selection tab

    const toggle = root.root.findAll(
      (node: any) => node.props?.children === "Xem nguồn gốc"
    );
    expect(toggle.length).toBeGreaterThan(0);
    expect(toggle[0].type).toBe("button");
    // No dummy anchor, no generic evidence endpoint link, no download/open.
    expect(root.root.findAll((node: any) => node.type === "a").length).toBe(0);

    act(() => { toggle[0].props.onClick(); });

    const filename = root.root.findByProps({ "data-evidence-filename": "true" });
    expect(String(filename.props.children)).toContain("quote.pdf");
    const fileId = root.root.findByProps({ "data-evidence-file-id": "ev-1" });
    expect(String(fileId.props.children)).toContain("ev-1");
    const status = root.root.findByProps({ "data-evidence-status": "true" });
    expect(String(status.props.children)).toContain("active");
  });

  it("supports keyboard row activation and Vietnamese history labels", async () => {
    const line = makeLine({
      state: "stale",
      current_selection: makeCurrentSelection(),
      history: [
        { selection_revision: 1, quote_line_id: "quote-1", supplier_name: "ABB Vietnam", quoted_unit_price: 850, currency: "USD", difference_amount: -150, difference_percent: -15, warnings: [], confirmed_by_user_id: "user-1", confirmed_at: "2026-09-05T00:00:00Z" },
      ],
    });
    mockUseNccSelection.mockReturnValue({
      aggregate: makeAggregate([line]),
      state: "READY",
      error: null,
      retry: vi.fn(),
      reload: vi.fn(),
    });

    let root: any;
    await act(async () => { root = renderPage(); });

    const row = root.root.findByProps({ "data-asset-line-id": "line-1" });
    expect(row.props.tabIndex).toBe(0);
    act(() => { row.props.onKeyDown({ key: "Enter", preventDefault: () => {} }); });
    // Drawer opened via keyboard.
    expect(root.root.findAllByProps({ role: "dialog" }).length).toBeGreaterThan(0);

    switchTab(root, 2); // history tab
    const items = root.root.findAllByProps({ "data-revision": 1 });
    expect(items.length).toBeGreaterThan(0);
    const label = items[0].findAll((node: any) => node.type === "strong")[0];
    expect(String(label.props.children)).toContain("Lần chọn 1");
    expect(String(label.props.children)).not.toContain("Rev");
  });

  it("disables ineligible candidate radio and prevents confirmation CTA or execution", async () => {
    const ineligibleCandidate = makeCandidate({
      quote_line_id: "quote-ineligible",
      supplier_name: "Ineligible Supplier",
      eligible: false,
    });
    mockUseNccSelection.mockReturnValue({
      aggregate: makeAggregate([makeLine({ candidates: [ineligibleCandidate] })]),
      state: "READY",
      error: null,
      retry: vi.fn(),
      reload: vi.fn(),
    });

    let root: any;
    await act(async () => { root = renderPage(); });
    openDrawer(root);

    const candidate = root.root.findByProps({ "data-candidate-id": "quote-ineligible" });
    const radio = candidate.findAllByProps({ type: "radio" })[0];
    expect(radio.props.disabled).toBe(true);

    // Attempting selection on disabled candidate does not show confirmation CTA
    act(() => { radio.props.onChange(); });
    expect(root.root.findAllByProps({ "data-primary-action": "true" })).toHaveLength(0);
    expect(mockConfirm).not.toHaveBeenCalled();
  });

  it("displays candidate comparison with server prices, delta, em dash percent, evidence summary, and exactly one primary confirmation CTA", async () => {
    const candidate = makeCandidate({
      quoted_unit_price: 850,
      currency: "USD",
      difference_amount: -150,
      difference_percent: null,
      evidence: { evidence_file_id: "ev-1", filename: "quote_doc.pdf", status: "verified" },
      eligible: true,
    });
    mockUseNccSelection.mockReturnValue({
      aggregate: makeAggregate([makeLine({ appraised_unit_price: 1000, candidates: [candidate] })]),
      state: "READY",
      error: null,
      retry: vi.fn(),
      reload: vi.fn(),
    });

    let root: any;
    await act(async () => { root = renderPage(); });
    openDrawer(root);

    // Initially no primary action
    expect(root.root.findAllByProps({ "data-primary-action": "true" })).toHaveLength(0);

    const candidateNode = root.root.findByProps({ "data-candidate-id": "quote-1" });
    const radio = candidateNode.findAllByProps({ type: "radio" })[0];
    act(() => { radio.props.onChange(); });

    // Exactly one primary confirmation CTA when eligible selected
    const primaryCta = root.root.findAllByProps({ "data-primary-action": "true" });
    expect(primaryCta).toHaveLength(1);
    expect(primaryCta[0].type).toBe("button");

    // Comparison dl displays server prices, delta, em dash percent, evidence filename and status
    const comparison = root.root.findByProps({ className: "ncc-selection-comparison" });
    const dds = comparison.findAll((node: any) => node.type === "dd");
    const getDdText = (dd: any) => {
      const c = dd.props.children;
      return Array.isArray(c) ? c.join("") : String(c ?? "");
    };

    expect(getDdText(dds[0])).toBe(new Intl.NumberFormat("vi-VN").format(1000));
    expect(getDdText(dds[1])).toContain("850");
    expect(getDdText(dds[1])).toContain("USD");
    expect(getDdText(dds[2])).toBe(new Intl.NumberFormat("vi-VN").format(-150));
    expect(getDdText(dds[3])).toBe("—");
    expect(getDdText(dds[4])).toBe("quote_doc.pdf");
    expect(getDdText(dds[5])).toBe("verified");
  });

  it("updates row aria-selected state and activates selection via Space key", async () => {
    mockUseNccSelection.mockReturnValue({
      aggregate: makeAggregate([makeLine()]),
      state: "READY",
      error: null,
      retry: vi.fn(),
      reload: vi.fn(),
    });

    let root: any;
    await act(async () => { root = renderPage(); });

    let row = root.root.findByProps({ "data-asset-line-id": "line-1" });
    expect(row.props["aria-selected"]).toBeUndefined();

    // Activate row via Space key
    act(() => {
      row.props.onKeyDown({ key: " ", preventDefault: () => {} });
    });

    row = root.root.findByProps({ "data-asset-line-id": "line-1" });
    expect(row.props["aria-selected"]).toBe("true");
    expect(root.root.findAllByProps({ role: "dialog" })).toHaveLength(1);

    // Closing the drawer deselects the line and clears aria-selected
    act(() => {
      root.root.findByProps({ className: "ncc-drawer-close" }).props.onClick();
    });
    row = root.root.findByProps({ "data-asset-line-id": "line-1" });
    expect(row.props["aria-selected"]).toBeUndefined();
    expect(root.root.findAllByProps({ role: "dialog" })).toHaveLength(0);
  });

  it("provides accessible drawer dialog semantics and close action", async () => {
    mockUseNccSelection.mockReturnValue({
      aggregate: makeAggregate([makeLine()]),
      state: "READY",
      error: null,
      retry: vi.fn(),
      reload: vi.fn(),
    });

    let root: any;
    await act(async () => { root = renderPage(); });
    openDrawer(root);

    const dialog = root.root.findByProps({ role: "dialog" });
    expect(dialog.props["aria-modal"]).toBe("true");
    expect(dialog.props["aria-label"]).toBe("Chi tiết dòng tài sản");
    expect(dialog.props["data-open"]).toBe("true");

    const closeBtn = root.root.findByProps({ className: "ncc-drawer-close" });
    expect(closeBtn.props["aria-label"]).toBe("Đóng");
    expect(closeBtn.props.type).toBe("button");

    act(() => { closeBtn.props.onClick(); });
    expect(root.root.findAllByProps({ role: "dialog" })).toHaveLength(0);
  });
});

describe("mapConfirmError (real mapping)", () => {
  it("recognizes detail.error_code from the backend 409 shape", () => {
    expect(
      mapConfirmError({ status: 409, detail: { error_code: "selection_revision_conflict" } }).kind
    ).toBe("version_conflict");
  });

  it("recognizes the nested ApiError detail.detail.error_code shape", () => {
    expect(
      mapConfirmError({
        status: 409,
        detail: { detail: { error_code: "selection_revision_conflict" } },
      }).kind
    ).toBe("version_conflict");
  });

  it("keeps recognizing legacy code shapes and rejects non-409 errors", () => {
    expect(mapConfirmError({ status: 409, code: "selection_revision_conflict" }).kind).toBe(
      "version_conflict"
    );
    expect(
      mapConfirmError({ status: 409, detail: { code: "selection_revision_conflict" } }).kind
    ).toBe("version_conflict");
    expect(mapConfirmError({ status: 500 }).kind).toBe("error");
    expect(mapConfirmError({ status: 409, detail: { error_code: "other" } }).kind).toBe("error");
  });

});
