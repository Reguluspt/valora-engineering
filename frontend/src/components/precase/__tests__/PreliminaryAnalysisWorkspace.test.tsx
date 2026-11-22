import React from "react";
import { act, create } from "react-test-renderer";
import { describe, expect, it, vi } from "vitest";

import type { ProjectAssetImportStagingRowResponse } from "../../../api/assetImports";
import type { PreliminaryAnalysisReadResponse } from "../../../api/preliminaryAnalysis";
import type { AnalysisPresentation } from "../analysisPresentation";
import { draftFromStaging, type AnalysisDraft } from "../analysisReviewModel";
import { AnalysisSourcesPanel } from "../AnalysisSourcesPanel";
import { decodeSourceBackup, encodeSourceBackup } from "../analysisSourceDraftBackup";
import { canAutosaveSource, newSourceDraft, useAnalysisSourceDrafts, type SourceDraftStorage } from "../analysisSourceDrafts";
import { PreliminaryAnalysisWorkspace } from "../PreliminaryAnalysisWorkspace";
import { SidebarCollapseContext } from "../../layout/SidebarCollapseContext";

vi.mock("@fluentui/react-components", async (importOriginal) => {
  const original = await importOriginal<typeof import("@fluentui/react-components")>();
  return { ...original, TabList: ({ children, selectedValue, onTabSelect, ...props }: any) => <div {...props} role="tablist">{React.Children.map(children, child => React.isValidElement(child) ? React.cloneElement(child as React.ReactElement<any>, { selected: child.props.value === selectedValue, onClick: (event: unknown) => onTabSelect(event, { value: child.props.value }) }) : child)}</div>,
    Tab: ({ children, value, selected, onClick, ...props }: any) => <button {...props} role="tab" aria-selected={selected} onClick={onClick}>{children}</button> };
});

const sourceRows: ProjectAssetImportStagingRowResponse[] = [
  { id: "row-a", import_batch_id: "batch-1", source_row_number: 17, proposed_asset_name: "Máy cắt",
    proposed_description: "Thiết bị cắt công nghiệp với mô tả dài từ tệp nguồn hiện hành", proposed_unit: "Máy",
    proposed_raw_price: "1.200.000", proposed_currency: "VND", proposed_quantity: "2",
    validation_status: "pending", validation_errors: [], validation_warnings: [] },
  { id: "row-b", import_batch_id: "batch-1", source_row_number: 42, proposed_asset_name: "Máy bơm",
    proposed_description: "Bơm cho hệ thống nước", proposed_unit: "Bộ", proposed_quantity: "3",
    validation_status: "pending", validation_errors: [], validation_warnings: [] },
  { id: "row-c", import_batch_id: "batch-1", source_row_number: 92, proposed_asset_name: "Máy ép",
    proposed_quantity: "1", validation_status: "pending", validation_errors: [], validation_warnings: [] },
];
const drafts = () => sourceRows.map(draftFromStaging);

function mount(options: { lines?: AnalysisDraft[]; disabled?: boolean; snapshot?: PreliminaryAnalysisReadResponse; presentation?: AnalysisPresentation; onConditionChange?: (row: number, field: "vat" | "delivery", value: string) => void; collapseSidebar?: () => void; localSourceDrafts?: boolean } = {}) {
  const onUpdateDraft = vi.fn();
  const onViewedCountChange = vi.fn();
  const headingFocus = vi.fn();
  const rowFocus = vi.fn();
  let renderer: ReturnType<typeof create>;
  act(() => {
    renderer = create(<SidebarCollapseContext.Provider value={options.collapseSidebar}><PreliminaryAnalysisWorkspace drafts={options.lines ?? drafts()} sourceRows={sourceRows}
      disabled={options.disabled ?? false} snapshot={options.snapshot} onUpdateDraft={onUpdateDraft}
      onViewedCountChange={onViewedCountChange} presentation={options.presentation}
      onReferenceConditionChange={options.onConditionChange} localSourceDrafts={options.localSourceDrafts} /></SidebarCollapseContext.Provider>, {
      createNodeMock: (element) => element.type === "h2" ? { focus: headingFocus }
        : element.type === "button" && element.props["aria-label"]?.startsWith("Xem chi tiết dòng") ? { focus: rowFocus }
          : null,
    });
  });
  return { renderer: renderer!, onUpdateDraft, onViewedCountChange, headingFocus, rowFocus };
}

function input(renderer: ReturnType<typeof create>, name: string) {
  return renderer.root.findAllByType("input").find((node) => node.props.name === name)!;
}
function selectRow(renderer: ReturnType<typeof create>, rowNumber: number) {
  act(() => renderer.root.findAllByType("button").find((node) =>
    node.props["aria-label"]?.startsWith(`Xem chi tiết dòng ${rowNumber}:`))!.props.onClick());
}
function search(renderer: ReturnType<typeof create>, value: string) {
  act(() => renderer.root.findAllByType("input").find((node) => node.props.type === "search")!.props.onChange({ target: { value } }));
}

function sourceButton(renderer: ReturnType<typeof create>, label: string) {
  return renderer.root.findAllByType("button").find(node => (node.props["aria-label"] ?? node.children.filter(child => typeof child === "string").join("")) === label)!;
}
function authoring(renderer: ReturnType<typeof create>) {
  return renderer.root.findAllByType("textarea").find(node => node.props["aria-label"] === "Diễn giải, URL hoặc ảnh clipboard")!;
}
function pasteSource(renderer: ReturnType<typeof create>, text: string, files: File[] = []) {
  const preventDefault = vi.fn();
  act(() => authoring(renderer).props.onPaste({ preventDefault, clipboardData: { getData: () => text,
    items: files.map(file => ({ type: file.type, getAsFile: () => file })) }, currentTarget: { selectionStart: 0, selectionEnd: 0 } }));
  return preventDefault;
}

describe("Independent source drafts", () => {

  it("recognizes and edits a URL from multiline input without replacing the narrative or source", () => {
    const { renderer } = mount({ localSourceDrafts: true });
    selectRow(renderer, 17);
    act(() => sourceButton(renderer, "+ Thêm nguồn giá").props.onClick());
    const card = () => renderer.root.findAllByType("article").find(node => node.props["data-source-draft"])!;
    const id = card().props["data-source-draft"];
    const initial = "Khảo sát\nhttps://example.com/catalog/pump-110!\nHàng có sẵn";
    act(() => authoring(renderer).props.onChange({ target: { value: initial } }));
    expect(renderer.root.findByType("code").children.join("")).toBe("https://example.com/catalog/pump-110!");
    const edited = initial.replace("pump-110", "pump-120");
    act(() => authoring(renderer).props.onChange({ target: { value: edited } }));
    expect(authoring(renderer).props.value).toBe(edited);
    expect(renderer.root.findByType("code").children.join("")).toBe("https://example.com/catalog/pump-120!");
    expect(renderer.root.findAllByProps({ "data-source-draft": id })).toHaveLength(1);
    act(() => renderer.unmount());
  });

  it("keeps punctuation in URL paths and leaves explicitly delimited prose punctuation in the narrative", () => {
    const { renderer } = mount({ localSourceDrafts: true });
    selectRow(renderer, 17);
    act(() => sourceButton(renderer, "+ Thêm nguồn giá").props.onClick());
    const url = "https://example.com/catalog/(pump),valve;A&B%21!'";
    const narrative = `Xem <${url}>, rồi đối chiếu.`;
    act(() => authoring(renderer).props.onChange({ target: { value: narrative } }));
    expect(authoring(renderer).props.value).toBe(narrative);
    expect(renderer.root.findByType("code").children.join("")).toBe(url);
    act(() => sourceButton(renderer, "Sửa URL").props.onClick());
    const edit = renderer.root.findAllByType("input").find(node => node.props.value === url)!;
    act(() => edit.props.onChange({ target: { value: "https://example.com/login!" } }));
    expect(sourceButton(renderer, "Áp dụng URL").props.disabled).toBe(false);
    const corrected = "https://example.com/catalog/(pump),valve;A&B%21!";
    act(() => edit.props.onChange({ target: { value: corrected } }));
    act(() => sourceButton(renderer, "Áp dụng URL").props.onClick());
    expect(authoring(renderer).props.value).toBe(narrative);
    expect(renderer.root.findByType("code").children.join("")).toBe(corrected);
    act(() => renderer.unmount());
  });

  it.each([
    ["https://example.com/quote", "1250000.5", true],
    ["https://example.com/quote", "", false],
    ["https://example.com/quote", "0", false],
    ["https://example.com/quote", "12.", false],
    ["https://example.com/quote", "1.250.000", false],
    ["http://example.com/quote", "12", false],
    ["javascript:void(0)", "12", false],
    ["https://user:placeholder@example.com", "12", false],
    ["https://example.com/login", "30000000", true],
    ["https://example.com/auth", "30000000", true],
    ["https://example.com/redirect", "12", true],
    ["https://example.com/quote?variant=1#price", "12", true],
    ["https://example.test/quote", "12", true],
    ["https://127.0.0.1:8443/quote", "12", true],
    ["https://[::1]/quote", "12", true],
    ["https://example.com/auth#access_token=placeholder", "12", false],
    ["https://example.com/login?%74oken=placeholder", "12", false],
    ["https:///example.com", "12", false],
  ] as const)("validates the saved price and link %s / %s", (url, price, expected) => {
    expect(canAutosaveSource({ url, price, narrative: "" })).toBe(expected);
  });

  it("blocks persistence and backup of credentials in narrative URLs while preserving the safe draft URL", () => {
    const source = { ...newSourceDraft("https://example.com/login"), price: "30000000" };
    const backup = encodeSourceBackup("12", 17, [source])!;
    expect(decodeSourceBackup(backup, "12", 17)).toMatchObject([{ id: source.id, url: source.url, price: source.price }]);
    const narrative = "Xem <https://example.com/auth?access_token=placeholder> để đối chiếu.";
    const unsafe = { ...source, narrative };
    expect(canAutosaveSource(unsafe)).toBe(false);
    expect(encodeSourceBackup("12", 17, [unsafe])).toBeNull();
    const imported = JSON.parse(backup);
    imported.drafts[0].narrative = narrative;
    expect(() => decodeSourceBackup(JSON.stringify(imported), "12", 17)).toThrow("Invalid draft backup");
  });

  it("debounces independent sources and retains a committed revision for retry after readback failure", async () => {
    vi.useFakeTimers();
    const save = vi.fn<SourceDraftStorage["save"]>()
      .mockResolvedValueOnce({ version: 1, verified: true })
      .mockResolvedValueOnce({ version: 1, verified: true })
      .mockResolvedValueOnce({ version: 2, verified: false })
      .mockRejectedValueOnce(new Error("Storage denied"))
      .mockResolvedValueOnce({ version: 3, verified: true });
    const storage: SourceDraftStorage = { scope: "12", load: async () => [], save, remove: async () => {} };
    let actions!: ReturnType<typeof useAnalysisSourceDrafts>;
    let renderer: ReturnType<typeof create> | undefined;
    function Harness() { actions = useAnalysisSourceDrafts(true, storage); return null; }
    const tick = (ms: number) => act(async () => { await vi.advanceTimersByTimeAsync(ms); });
    try {
      await act(async () => { renderer = create(<Harness />); });
      act(() => { actions.add(17); actions.add(42, "https://example.com/second"); });
      const a = actions.byRow[17][0].id, b = actions.byRow[42][0].id;
      act(() => { actions.patch(17, a, { url: "https://example.com/first!", price: "10" }); });
      await tick(400);
      act(() => { actions.patch(17, a, { price: "11.5" }); actions.patch(42, b, { price: "20" }); });
      await tick(799);
      expect(save).not.toHaveBeenCalled();
      expect(actions.statusFor(actions.byRow[17][0])).toBe("saving");
      await tick(1);
      expect(save.mock.calls.map(([row, draft, revision]) => [row, draft.id, draft.price, draft.url, revision])).toEqual([
        [17, a, "11.5", "https://example.com/first!", 0], [42, b, "20", "https://example.com/second", 0],
      ]);
      expect(actions.statusFor(actions.byRow[17][0])).toBe("saved");
      act(() => actions.patch(17, a, { price: "13" }));
      await tick(800);
      expect(save.mock.calls[2]).toMatchObject([17, { id: a, price: "13" }, 1]);
      expect(actions.statusFor(actions.byRow[17][0])).toBe("failed");
      expect(actions.statusFor(actions.byRow[42][0])).toBe("saved");
      act(() => actions.patch(42, b, { price: "21" }));
      await tick(800);
      expect(actions.statusFor(actions.byRow[42][0])).toBe("failed");
      act(() => actions.patch(17, a, { price: "14" }));
      expect(actions.statusFor(actions.byRow[17][0])).toBe("saving");
      await tick(800);
      expect(save.mock.calls[4]).toMatchObject([17, { id: a, price: "14" }, 2]);
      expect(actions.statusFor(actions.byRow[17][0])).toBe("saved");
      expect(actions.statusFor(actions.byRow[42][0])).toBe("failed");
    } finally {
      act(() => renderer?.unmount());
      vi.useRealTimers();
    }
  });

  it("renders the compact source form and retains existing metadata when the source price is edited", () => {
    let actions: ReturnType<typeof useAnalysisSourceDrafts>;
    function SourcePanel() {
      actions = useAnalysisSourceDrafts(true);
      return <AnalysisSourcesPanel row={17} drafts={actions.byRow[17] ?? []} actions={actions} editable fixture />;
    }

    let renderer: ReturnType<typeof create>;
    act(() => { renderer = create(<SourcePanel />); });
    act(() => actions.add(17));
    const source = actions!.byRow[17][0];
    const metadata = {
      title: "Máy cắt",
      origin: "Báo giá của nhà cung cấp",
      specifications: "Model A1",
      currency: "USD",
      unit: "Máy",
      capturedAt: "2026-11-05",
    };
    act(() => actions.patch(17, source.id, metadata));

    const root = renderer!.root;
    const editor = root.findByProps({ className: "analysis-source-editor" });
    const price = editor.findByType("input");
    expect(price.props["aria-label"]).toBe("Giá khảo sát");
    expect(editor.findByProps({ id: price.props["aria-describedby"] }).props["data-save-status"]).toBe("session");
    expect(editor.findByProps({ className: "analysis-sr-only analysis-source-save-announcement" }).props.role).toBe("status");
    expect(editor.findAllByType("label").map(label => label.findAllByType("span")[0].children.join(""))).toEqual([
      "Loại nguồn", "Diễn giải, URL hoặc ảnh clipboard", "Giá khảo sát", "VAT", "Vận chuyển", "Đánh giá riêng cho tài sản này (nháp)",
    ]);
    expect(root.findByProps({ className: "analysis-source-price" }).findByType("strong").children).toEqual(["—"]);
    act(() => price.props.onChange({ target: { value: "1250000" } }));
    act(() => sourceButton(renderer!, "Thu gọn nguồn giá 01").props.onClick());
    expect(root.findAllByProps({ className: "analysis-source-editor" })).toHaveLength(0);
    const detail = sourceButton(renderer!, "Xem chi tiết nguồn giá 01");
    expect(detail.children).toContain("Xem chi tiết");
    expect(detail.props["aria-expanded"]).toBe(false);
    const card = root.findByType("article");
    const cardText = JSON.stringify(renderer!.toJSON());
    expect(card.props["aria-label"]).toBe("Nguồn giá 01");
    expect(card.findByType("strong").children.join("")).toBe("1.250.000 USD");
    expect(card.findAllByType("p").map(node => node.children.join(""))).toContain("0 URL · 0 ảnh chứng cứ");
    expect(cardText).not.toMatch(/Giá quan sát|Chưa nhập website|Chưa nhập ĐVT|Thu thập:/);
    act(() => detail.props.onClick());
    expect(sourceButton(renderer!, "Thu gọn nguồn giá 01").props["aria-expanded"]).toBe(true);
    expect(actions!.byRow[17][0]).toEqual({ ...source, ...metadata, price: "1250000" });
    act(() => renderer!.unmount());
  });

  it.each([0, 1, 2, 3, 12])("retains %i independent drafts across asset selection without changing the manual price", (count) => {
    const lines = drafts(); lines[0].proposed_unit_price = "987654321";
    const { renderer, onUpdateDraft } = mount({ lines, localSourceDrafts: true });
    selectRow(renderer, 17);
    for (let index = 0; index < count; index++) {
      act(() => sourceButton(renderer, "+ Thêm nguồn giá").props.onClick());
      pasteSource(renderer, `https://example.com/source-${index}`);
      act(() => renderer.root.findAllByType("input").find(node => node.props["aria-label"] === "Giá khảo sát")!.props.onChange({ target: { value: String((index + 1) * 1000) } }));
    }
    const cards = () => renderer.root.findAllByType("article").filter(node => node.props["data-source-draft"]);
    expect(cards()).toHaveLength(count);
    expect(new Set(cards().map(node => node.props["data-source-draft"])).size).toBe(count);
    selectRow(renderer, 42); expect(cards()).toHaveLength(0);
    selectRow(renderer, 17); expect(cards()).toHaveLength(count);
    for (let index = 0; index < count; index++) {
      act(() => sourceButton(renderer, `Xem chi tiết nguồn giá ${String(index + 1).padStart(2, "0")}`).props.onClick());
      expect(renderer.root.findAllByType("code").map(node => node.children.join(""))).toContain(`https://example.com/source-${index}`);
      expect(renderer.root.findAllByType("input").find(node => node.props["aria-label"] === "Giá khảo sát")!.props.value).toBe(`${index + 1}.000`);
    }
    expect(input(renderer, "proposed_unit_price").props.value).toBe("987.654.321");
    expect(onUpdateDraft).not.toHaveBeenCalled();
    act(() => renderer.unmount());
  });

  it("keeps paragraphs, resolves second URLs explicitly and evaluates only the selected draft", () => {
    const { renderer, onUpdateDraft } = mount({ localSourceDrafts: true }); selectRow(renderer, 17);
    act(() => sourceButton(renderer, "+ Thêm nguồn giá").props.onClick({ preventDefault: vi.fn(), stopPropagation: vi.fn() }));
    const narrative = "Căn cứ giá\n\nĐiều kiện và hạn chế " + "dài ".repeat(30);
    act(() => authoring(renderer).props.onChange({ target: { value: narrative } }));
    expect(pasteSource(renderer, "https://example.com/a! https://example.com/b,(2); https://example.com/a!")).toHaveBeenCalledOnce();
    expect(renderer.root.findAllByType("code").map(node => node.children.join(""))).toEqual(["https://example.com/a!", "https://example.com/b,(2);"]);
    act(() => sourceButton(renderer, "Thay link hiện tại").props.onClick());
    expect(renderer.root.findByType("code").children.join("")).toBe("https://example.com/b,(2);");
    expect(authoring(renderer).props.value).toBe(narrative);
    pasteSource(renderer, "https://example.com/c");
    act(() => sourceButton(renderer, "Tạo nguồn mới với URL này").props.onClick());
    expect(renderer.root.findByType("code").children.join("")).toBe("https://example.com/c");
    act(() => renderer.root.findByProps({ className: "analysis-source-editor" }).findAllByType("select").at(-1)!.props.onChange({ target: { value: "accepted" } }));
    expect(JSON.stringify(renderer.toJSON())).toContain("Chấp nhận làm cơ sở");
    act(() => authoring(renderer).props.onChange({ target: { value: "Thay đổi sau đánh giá" } }));
    expect(JSON.stringify(renderer.toJSON())).toContain("Nội dung đã đổi, cần rà soát lại");
    act(() => renderer.root.findByProps({ className: "analysis-source-editor" }).findAllByType("select").at(-1)!.props.onChange({ target: { value: "review" } }));
    expect(JSON.stringify(renderer.toJSON())).not.toContain("Nội dung đã đổi, cần rà soát lại");
    act(() => sourceButton(renderer, "Xóa bản nháp nguồn giá 02").props.onClick());
    act(() => sourceButton(renderer, "Xem chi tiết nguồn giá 01").props.onClick());
    expect(authoring(renderer).props.value).toBe(narrative);
    expect(renderer.root.findByProps({ className: "analysis-source-editor" }).findAllByType("select").at(-1)!.props.value).toBe("unreviewed");
    expect(onUpdateDraft).not.toHaveBeenCalled();
    act(() => renderer.unmount());
  });

  it("attaches images to one draft and revokes object URLs on removal and unmount", () => {
    const createUrl = vi.spyOn(URL, "createObjectURL").mockReturnValueOnce("blob:one").mockReturnValueOnce("blob:two").mockReturnValueOnce("blob:three");
    const revoke = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
    const { renderer, onUpdateDraft } = mount({ localSourceDrafts: true }); selectRow(renderer, 17);
    act(() => sourceButton(renderer, "+ Thêm nguồn giá").props.onClick());
    act(() => authoring(renderer).props.onChange({ target: { value: "Giữ diễn giải" } }));
    const image = new File([new Uint8Array([1, 2, 3])], "evidence.png", { type: "image/png" });
    pasteSource(renderer, "https://example.com/catalog/pump-110", [image]);
    expect(renderer.root.findByType("img").props.src).toBe("blob:one");
    expect(renderer.root.findByType("code").children.join("")).toBe("https://example.com/catalog/pump-110");
    expect(authoring(renderer).props.value).toBe("Giữ diễn giải");
    expect(renderer.root.findAllByType("article").filter(node => node.props["data-source-draft"])).toHaveLength(1);
    act(() => sourceButton(renderer, "Xóa ảnh 1").props.onClick()); expect(revoke).toHaveBeenCalledWith("blob:one");
    pasteSource(renderer, "", [image]);
    act(() => sourceButton(renderer, "Xóa bản nháp nguồn giá 01").props.onClick()); expect(revoke).toHaveBeenCalledWith("blob:two");
    act(() => sourceButton(renderer, "+ Thêm nguồn giá").props.onClick()); pasteSource(renderer, "", [image]);
    act(() => renderer.unmount()); expect(revoke).toHaveBeenCalledWith("blob:three");
    expect(onUpdateDraft).not.toHaveBeenCalled(); createUrl.mockRestore(); revoke.mockRestore();
  });

  it("rejects unsafe URLs and unsupported or oversized images without losing the existing draft", () => {
    const { renderer } = mount({ localSourceDrafts: true }); selectRow(renderer, 17);
    act(() => sourceButton(renderer, "+ Thêm nguồn giá").props.onClick());
    pasteSource(renderer, "https://example.com/original");
    const unsafe = "https://example.com/catalog?access_token=placeholder#price";
    act(() => authoring(renderer).props.onChange({ target: { value: unsafe } }));
    expect(authoring(renderer).props.value).toBe(unsafe);
    expect(JSON.stringify(renderer.toJSON())).toContain("Hãy bỏ tài khoản, mật khẩu hoặc mã truy cập khỏi URL");
    expect(renderer.root.findByType("code").children.join("")).toBe("https://example.com/original");
    act(() => authoring(renderer).props.onChange({ target: { value: "Xem https://example.com/login!, rồi xác minh" } }));
    expect(JSON.stringify(renderer.toJSON())).toContain("Cần xác minh nguồn");
    expect(renderer.root.findAllByType("code").map(node => node.children.join(""))).toEqual(["https://example.com/original", "https://example.com/login!,"]);
    pasteSource(renderer, "", [new File(["<svg/>"], "bad.svg", { type: "image/svg+xml" }), new File([new Uint8Array(10 * 1024 * 1024 + 1)], "large.png", { type: "image/png" })]);
    expect(renderer.root.findAllByType("img")).toHaveLength(0);
    expect(JSON.stringify(renderer.toJSON())).toContain("10 MiB"); act(() => renderer.unmount());
  });

  it("keeps real-mode actions disabled and does not count suggested source totals as registered or accepted", () => {
    const { renderer, onUpdateDraft } = mount({ presentation: { projectCode: "T", catalogName: "T", assets: { 17: {
      code: "T-17", status: "Chưa xác nhận", statusTone: "gray", viewed: false, manual: true, referenceCount: 9, evidenceCount: 0,
      reference: { name: "Hồ sơ cũ", kind: "Kết quả thẩm định", date: "2026-11-05", price: "1000", vat: "Chưa xác định", delivery: "Chưa xác định" },
    } } } });
    selectRow(renderer, 17);
    expect(sourceButton(renderer, "+ Thêm nguồn giá").props.disabled).toBe(true);
    act(() => sourceButton(renderer, "+ Thêm nguồn giá").props.onClick({ preventDefault: vi.fn(), stopPropagation: vi.fn() }));
    expect(renderer.root.findAllByType("article").filter(node => node.props["data-source-draft"])).toHaveLength(0);
    expect(JSON.stringify(renderer.toJSON())).toContain("HỆ THỐNG GỢI Ý · CHƯA XÁC MINH");
    expect(JSON.stringify(renderer.toJSON())).toContain("0 nháp · 1 gợi ý");
    expect(JSON.stringify(renderer.toJSON())).not.toContain("✓ Ưu tiên");
    expect(onUpdateDraft).not.toHaveBeenCalled(); act(() => renderer.unmount());
  });
});

describe("PreliminaryAnalysisWorkspace presentation", () => {
  it("presents survey price as copyable read-only output and leaves reference price editable", () => {
    const { renderer, onUpdateDraft } = mount({ presentation: { projectCode: "T", catalogName: "T", assets: {
      17: { status: "Chưa xác nhận", statusTone: "gray", referenceCount: 0, evidenceCount: 0, viewed: false, manual: true, surveyPrice: "92400000" },
    } } });
    selectRow(renderer, 17);
    const survey = renderer.root.findByType("output");
    expect(survey.props["aria-label"]).toBe("Giá khảo sát");
    expect(survey.children).toEqual(["92.400.000"]);
    expect(survey.props.tabIndex).toBe(0);
    expect(input(renderer, "confirmed_reference_price").props.disabled).toBe(false);
    expect(onUpdateDraft).not.toHaveBeenCalled();
  });

  it("reports the full basis limit without accepting an oversized change", () => {
    const lines = drafts();
    lines[0].accepted_price_basis = "a".repeat(64);
    const { renderer, onUpdateDraft } = mount({ lines });
    selectRow(renderer, 17);
    const basis = renderer.root.findAllByType("textarea").find(node => node.props.name === "accepted_price_basis")!;
    expect(JSON.stringify(renderer.toJSON())).toContain("Đã đạt giới hạn 64 ký tự");
    act(() => basis.props.onChange({ target: { value: "a".repeat(65) } }));
    expect(onUpdateDraft).not.toHaveBeenCalled();
    expect(basis.props.value).toHaveLength(64);
    expect(JSON.stringify(renderer.toJSON())).toContain("Nội dung chưa được áp dụng");
  });

  it("centers just unit, source quantity and evidence cells for text, zero and missing values", () => {
    const lines = drafts();
    lines[0].quantity = "0";
    const { renderer } = mount({ lines, presentation: { projectCode: "T", catalogName: "T", assets: {
      17: { status: "Đã xem", statusTone: "gray", evidenceCount: 0 },
    } } });
    const rows = renderer.root.findByType("tbody").findAllByType("tr").map(row => row.findAllByType("td"));
    for (const cells of rows) {
      expect(cells.flatMap((cell, index) => cell.props.className?.includes("analysis-cell-centered") ? [index] : [])).toEqual([3, 4, 11]);
      for (const index of [5, 6, 7, 8, 9]) expect(cells[index].props.className).toContain("precase-analysis-workspace__numeric");
    }
    expect([rows[0][3].children.join(""), rows[0][4].children.join(""), rows[0][11].findByType("button").children.join("")]).toEqual(["Máy", "0", "0"]);
    expect(rows[1][11].findByType("button").children.join("")).toBe("—");
  });

  it("maximizes the same table and restores the open details without changing sidebar preference", () => {
    const collapseSidebar = vi.fn();
    const { renderer, onUpdateDraft } = mount({ collapseSidebar });
    selectRow(renderer, 42);
    expect(renderer.root.findByType("aside").props.hidden).toBe(false);
    const expand = renderer.root.findAllByType("button").find(node => node.props["aria-label"] === "Mở rộng bảng")!;
    const scrollTo = vi.fn();
    const focus = vi.fn();
    vi.stubGlobal("window", { scrollX: 8, scrollY: 42, scrollTo });
    try {
      act(() => expand.props.onClick({ detail: 1, currentTarget: { focus } }));
      expect(renderer.root.findAllByProps({ "data-layout": "TABLE_MAXIMIZED" })).toHaveLength(1);
      expect(renderer.root.findByType("aside").props.hidden).toBe(true);
      const trigger = { focus: vi.fn(), isConnected: true };
      act(() => sourceButton(renderer, "Xem nguồn giá dòng 17").props.onClick({ detail: 0, currentTarget: trigger }));
      expect(renderer.root.findByType("aside").props.hidden).toBe(false);
      expect(renderer.root.findByType("aside").props.role).toBe("dialog");
      expect(renderer.root.findByType("h2").children.join("")).toBe("Máy cắt");
      act(() => renderer.root.findByType("aside").props.onKeyDown({ key: "Escape", preventDefault: vi.fn() }));
      expect(renderer.root.findByType("aside").props.hidden).toBe(true);
      expect(renderer.root.findAllByProps({ "data-layout": "TABLE_MAXIMIZED" })).toHaveLength(1);
      expect(trigger.focus).toHaveBeenCalledWith({ preventScroll: true });
      const shrink = sourceButton(renderer, "Thu gọn bảng");
      act(() => shrink.props.onClick({ detail: 1, currentTarget: { focus } }));
      expect(renderer.root.findByType("aside").props.hidden).toBe(false);
      expect(scrollTo).toHaveBeenLastCalledWith({ left: 8, top: 42, behavior: "instant" });
      expect(collapseSidebar).not.toHaveBeenCalled();
    } finally {
      vi.unstubAllGlobals();
    }
    expect(renderer.root.findAllByType("tr").find(node => node.props["data-selected"] === "true")?.props["data-row-source"]).toBe(42);
    expect(onUpdateDraft).not.toHaveBeenCalled();
  });

  it("renders the approved column and tab order", () => {
    const { renderer } = mount();
    expect(renderer.root.findAllByType("th").map(node => node.findAllByType("span")[0].children.join(""))).toEqual([
      "STT", "Tài sản", "Đặc điểm", "ĐVT", "SL nguồn", "Đơn giá KH", "Thành tiền KH",
      "Giá khảo sát", "Đơn giá đề xuất", "Thành tiền đề xuất", "Nguồn", "Chứng cứ", "Trạng thái",
    ]);
    expect(renderer.root.findAllByType("button").filter(node => node.props.role === "tab").map(node => node.children.join("")))
      .toEqual(["Giá & chứng cứ", "Đặc điểm & SL", "Lịch sử"]);
  });

  it.each(Array.from({ length: 13 }, (_, index) => index))("resizes column %i by pointer and keyboard without editing a draft", (index) => {
    const { renderer, onUpdateDraft } = mount();
    const grips = () => renderer.root.findAllByProps({ role: "separator" });
    const grip = () => grips()[index].props;
    const width = () => renderer.root.findAllByType("col")[index].props.style.width;
    const initial = width();
    const target = { closest: () => ({ getBoundingClientRect: () => ({ width: width() }) }), setPointerCapture: vi.fn() };
    const pointer = { isPrimary: true, button: 0, pointerId: 7, clientX: 200, currentTarget: target, preventDefault: vi.fn() };
    expect(grips()).toHaveLength(13);
    expect(grip()["aria-label"]).toMatch(/^Đổi độ rộng cột /);
    act(() => grip().onPointerDown(pointer));
    expect(target.setPointerCapture).toHaveBeenCalledWith(7);
    act(() => grip().onPointerMove({ ...pointer, clientX: 240 }));
    expect(width()).toBe(initial + 40);
    act(() => grip().onPointerMove({ ...pointer, clientX: 0 }));
    expect(width()).toBe(grip()["aria-valuemin"]);
    act(() => grip().onPointerUp({ ...pointer, clientX: 0 }));
    expect(width()).toBe(grip()["aria-valuemin"]);
    act(() => grip().onKeyDown({ key: "ArrowRight", preventDefault: vi.fn() }));
    expect(width()).toBe(grip()["aria-valuemin"] + 8);
    act(() => grip().onKeyDown({ key: "ArrowLeft", preventDefault: vi.fn() }));
    selectRow(renderer, 42);
    search(renderer, "Máy bơm");
    expect(width()).toBe(grip()["aria-valuemin"]);
    expect(onUpdateDraft).not.toHaveBeenCalled();
    const reset = renderer.root.findAllByType("button").find(node => node.children.includes("Khôi phục độ rộng mặc định"))!;
    act(() => reset.props.onClick());
    expect(width()).toBe(initial);
    act(() => grip().onPointerDown(pointer));
    act(() => grip().onPointerMove({ ...pointer, clientX: 240 }));
    act(() => grip().onLostPointerCapture(pointer));
    expect(width()).toBe(initial);
  });

  it("keeps source conditions readable and only provides editing when the owner supplies an action", () => {
    const presentation: AnalysisPresentation = { projectCode: "Test", catalogName: "Danh mục", assets: {
      17: { code: "A-17", status: "Đã xem", statusTone: "gray", viewed: true, manual: true, referenceCount: 1, evidenceCount: 0,
        reference: { name: "Nguồn A", kind: "Báo giá", date: "2026-11-05", price: "1200000", vat: "Đã bao gồm", delivery: "Chưa xác định" } },
    } };
    const readOnly = mount({ presentation });
    selectRow(readOnly.renderer, 17);
    expect(readOnly.renderer.root.findByProps({ "aria-label": "VAT chỉ đọc" }).children).toEqual(["Đã bao gồm"]);
    expect(readOnly.renderer.root.findByProps({ "aria-label": "Vận chuyển chỉ đọc" }).children).toEqual(["Chưa xác định"]);
    const onConditionChange = vi.fn();
    const editable = mount({ presentation, onConditionChange });
    selectRow(editable.renderer, 17);
    const select = editable.renderer.root.findAllByType("select").find(node => node.props["aria-label"] === "VAT")!;
    act(() => select.props.onChange({ target: { value: "Chưa bao gồm" } }));
    expect(onConditionChange).toHaveBeenCalledExactlyOnceWith(17, "vat", "Chưa bao gồm");
    expect(editable.onUpdateDraft).not.toHaveBeenCalled();
  });

  it("moves focus for pointer and keyboard selection and tracks views without confirming rows", () => {
    const { renderer, onUpdateDraft, onViewedCountChange, headingFocus, rowFocus } = mount();
    const row = renderer.root.findAllByType("button").find(node => node.props["aria-label"]?.startsWith("Xem chi tiết dòng 17:"))!;
    const origin = () => renderer.root.findAllByType("div").find(node => node.props["data-focus-origin"])!.props["data-focus-origin"];
    act(() => row.props.onClick({ detail: 1 }));
    expect(origin()).toBe("pointer");
    expect(headingFocus).toHaveBeenCalledWith({ preventScroll: true });
    expect(onViewedCountChange).toHaveBeenLastCalledWith(1);
    act(() => renderer.root.findAllByType("button").find(node => node.children.includes("Tiếp theo →"))!.props.onClick({ detail: 0 }));
    expect(origin()).toBe("keyboard");
    expect(renderer.root.findByType("h2").children).toEqual(["Máy bơm"]);
    expect(onViewedCountChange).toHaveBeenLastCalledWith(2);
    expect(renderer.root.findAllByType("button").find(node => node.props["aria-label"] === "Đóng nền chi tiết tài sản")?.props.tabIndex).toBe(-1);
    act(() => renderer.root.findByType("aside").props.onKeyDown({ key: "Escape" }));
    expect(renderer.root.findAllByProps({ "aria-label": "Đóng nền chi tiết tài sản" })).toHaveLength(0);
    expect(rowFocus).toHaveBeenCalledWith({ preventScroll: true });
    expect(onUpdateDraft).not.toHaveBeenCalled();
  });

  it("keeps 150 rows bounded and navigates across the visible page boundary", () => {
    const lines = Array.from({ length: 150 }, (_, index) => ({
      ...draftFromStaging(sourceRows[0]), identity: `Tài sản ${index + 1}`, source_row_number: index + 101,
    }));
    const { renderer } = mount({ lines });
    expect(renderer.root.findAllByType("tbody")[0].findAllByType("tr")).toHaveLength(50);
    selectRow(renderer, 150);
    act(() => renderer.root.findAllByType("button").find(node => node.children.includes("Tiếp theo →"))!.props.onClick({ detail: 0 }));
    expect(renderer.root.findByType("h2").children).toEqual(["Tài sản 51"]);
    act(() => renderer.root.findAllByType("button").find(node => node.children.includes("Hiển thị dòng đang chọn"))!.props.onClick());
    expect(renderer.root.findByProps({ "data-row-source": 151 }).props["data-selected"]).toBe("true");
    act(() => renderer.root.findAllByType("button").find(node => node.children.includes("Trang sau"))!.props.onClick());
    expect(renderer.root.findByProps({ "data-row-source": 250 }).children[0].props.children).toBe(150);
  });

  it("shows available source fields and edits the original draft after search and selection", () => {
    const { renderer, onUpdateDraft } = mount();
    expect(JSON.stringify(renderer.toJSON())).toContain(sourceRows[0].proposed_description);
    expect(JSON.stringify(renderer.toJSON())).toContain("1.200.000");
    expect(JSON.stringify(renderer.toJSON())).toContain("VND");
    search(renderer, "hệ thống nước");
    expect(renderer.root.findAllByProps({ "data-row-source": 17 })).toHaveLength(0);
    expect(renderer.root.findAllByProps({ "data-row-source": 42 })).toHaveLength(1);
    selectRow(renderer, 42);
    expect(renderer.root.findByType("h2").children).toEqual(["Máy bơm"]);
    act(() => input(renderer, "proposed_unit_price").props.onChange({ target: { value: "1250000" } }));
    expect(onUpdateDraft).toHaveBeenCalledExactlyOnceWith(1, { proposed_unit_price: "1250000" });
  });

  it("keeps the source cell compact and opens the original filtered asset without changing price", () => {
    const { renderer, onUpdateDraft } = mount();
    search(renderer, "hệ thống nước");
    const cell = renderer.root.findByType("tbody").findByType("tr").findAllByType("td")[10];
    expect(cell.findAllByType("textarea")).toHaveLength(0);
    expect(cell.findAllByType("input")).toHaveLength(0);
    expect(cell.findAllByType("details")).toHaveLength(0);
    act(() => renderer.root.findAllByType("button").find(node => node.props.id === "analysis-tab-specs")!.props.onClick());
    act(() => cell.findByType("button").props.onClick({ detail: 1 }));
    expect(renderer.root.findAllByType("button").find(node => node.props.id === "analysis-tab-price")!.props["aria-selected"]).toBe(true);
    expect(onUpdateDraft).not.toHaveBeenCalled();
    expect(renderer.root.findByType("h2").children).toEqual(["Máy bơm"]);
    act(() => input(renderer, "confirmed_reference_price").props.onChange({ target: { value: "1000000" } }));
    expect(onUpdateDraft).toHaveBeenCalledExactlyOnceWith(1, { confirmed_reference_price: "1000000" });
    expect(renderer.root.findAllByType("input").some((node) => node.props.name?.startsWith("quantity"))).toBe(false);
    expect(renderer.root.findAllByType("textarea")[0].props.maxLength).toBe(64);
  });

  it("keeps stable identity through status filters, including sparse source row numbers", () => {
    const lines = drafts();
    lines[0].human_line_confirmed = true;
    lines[2].has_unresolved_blocking_line = true;
    const { renderer, onUpdateDraft } = mount({ lines });
    act(() => renderer.root.findByProps({ "aria-label": "Lọc trạng thái rà soát" }).findByType("select").props.onChange({ target: { value: "blocked" } }));
    expect(renderer.root.findAllByProps({ "data-row-source": 42 })).toHaveLength(0);
    selectRow(renderer, 92);
    expect(input(renderer, "human_line_confirmed").props.disabled).toBe(true);
    act(() => input(renderer, "has_unresolved_blocking_line").props.onChange({ currentTarget: { checked: false } }));
    expect(onUpdateDraft).toHaveBeenCalledExactlyOnceWith(2, { has_unresolved_blocking_line: false });
  });

  it("returns from the separate detail panel without resetting selection or edited values", () => {
    const lines = drafts();
    lines[1].proposed_unit_price = "1700000";
    const { renderer, onUpdateDraft } = mount({ lines });
    selectRow(renderer, 42);
    expect(renderer.root.findAllByType("div").some((node) => node.props.className === "precase-analysis-workspace is-detail-open")).toBe(true);
    act(() => renderer.root.findAllByType("button").find((node) => node.props["aria-label"] === "Đóng chi tiết tài sản")!.props.onClick());
    expect(renderer.root.findAllByType("div").some((node) => node.props.className === "precase-analysis-workspace")).toBe(true);
    expect(input(renderer, "proposed_unit_price").props.value).toBe("1.700.000");
    expect(renderer.root.findByProps({ "data-row-source": 42 }).props["data-selected"]).toBe("true");
    expect(onUpdateDraft).not.toHaveBeenCalled();
  });

  it("disables editing and ignores stale edit callbacks while the owning screen is locked", () => {
    const { renderer, onUpdateDraft } = mount({ disabled: true });
    for (const node of renderer.root.findAllByType("input").filter((node) => node.props.name)) expect(node.props.disabled).toBe(true);
    for (const node of renderer.root.findAllByType("textarea")) expect(node.props.disabled).toBe(true);
    act(() => input(renderer, "proposed_unit_price_row_42").props.onChange({ target: { value: "999" } }));
    act(() => renderer.root.findAllByType("textarea").find((node) => node.props.name === "accepted_price_basis")!.props.onChange({ target: { value: "Không được ghi" } }));
    act(() => input(renderer, "proposed_unit_price").props.onChange({ target: { value: "999" } }));
    act(() => input(renderer, "human_line_confirmed").props.onChange({ currentTarget: { checked: true } }));
    expect(onUpdateDraft).not.toHaveBeenCalled();
  });

  it("renders a committed snapshot read-only without substituting mutable staging source fields", () => {
    const snapshot: PreliminaryAnalysisReadResponse = {
      id: "snapshot-1", project_id: "project-1", version: 1, import_batch_id: "batch-1", source_artifact_id: "source-1",
      structure_snapshot_id: "structure-1", mapping_decision_id: "decision-1", mapping_profile_usage_id: "usage-1",
      mapping_decision_digest_sha256: "a".repeat(64), profile_usage_mapping_digest_sha256: "a".repeat(64),
      line_manifest_digest_sha256: "b".repeat(64), finalized_by_user_id: "reviewer-1", finalized_at: "2026-11-05T09:00:00Z",
      line_manifest: [{ source_row_number: 17, identity: "Máy cắt đã xác nhận", quantity: 2, accepted_price_basis: "Báo giá đã kiểm tra",
        confirmed_reference_price: 100, transport_percentage: 5, proposed_unit_price: 108, human_line_confirmed: true, has_unresolved_blocking_line: false }],
    };
    const { renderer, onUpdateDraft } = mount({ snapshot });
    expect(renderer.root.findAllByType("input").filter((node) => node.props.name)).toHaveLength(0);
    expect(renderer.root.findAllByType("textarea")).toHaveLength(0);
    expect(JSON.stringify(renderer.toJSON())).toContain("Bản phân tích đã chốt chỉ cho phép xem");
    expect(JSON.stringify(renderer.toJSON())).not.toContain(sourceRows[0].proposed_description);
    expect(JSON.stringify(renderer.toJSON())).not.toContain("1.200.000");
    expect(onUpdateDraft).not.toHaveBeenCalled();
  });
});
