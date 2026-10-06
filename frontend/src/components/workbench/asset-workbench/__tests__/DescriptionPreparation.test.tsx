import { act, create, type ReactTestRenderer } from "react-test-renderer";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { DescriptionPreparation } from "../DescriptionPreparation";
import { saveAssetLineDraft, commitAssetLineDraft, fetchProjectDraftState } from "../../../../api/projects";

vi.mock("../../../../api/projects", () => ({ saveAssetLineDraft: vi.fn(), commitAssetLineDraft: vi.fn(), fetchProjectDraftState: vi.fn() }));
vi.mock("@fluentui/react-components", () => ({
  Button: (props: any) => <button {...props} />,
  Textarea: (props: any) => <textarea {...props} />,
  Field: ({ children }: any) => <label>{children}</label>,
  Dialog: ({ open, children }: any) => open ? <div role="dialog">{children}</div> : null,
  DialogSurface: ({ children }: any) => <div>{children}</div>,
  DialogBody: ({ children }: any) => <div>{children}</div>,
  DialogTitle: ({ children }: any) => <h2>{children}</h2>,
  DialogContent: ({ children }: any) => <div>{children}</div>,
  DialogActions: ({ children }: any) => <div>{children}</div>,
}));
let root: ReactTestRenderer;
const committed = vi.fn();
const button = (label: string) => root.root.findAllByType("button").find(node => node.props.children === label)!;
const edit = (value: string) => act(() => root.root.findByType("textarea").props.onChange(null, { value }));
const click = async (label: string) => act(async () => { await button(label).props.onClick(); });
const mount = async (enabled = true) => act(async () => {
  root = create(<DescriptionPreparation projectId="project" sessionId="session" enabled={enabled} onCommitted={committed}
    row={{ project_asset_line_id: "line", line_no: 1, raw_name: "Máy", description: "Official value", quantity: 1, row_version: 7 }} />);
});
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(fetchProjectDraftState).mockResolvedValue({ items: [] } as any);
  vi.mocked(saveAssetLineDraft).mockResolvedValue({} as any);
  vi.mocked(commitAssetLineDraft).mockResolvedValue({} as any);
});
afterEach(() => { if (root) act(() => root.unmount()); });

it("keeps edits unofficial until saved and explicitly Human Committed with the exact row version", async () => {
  await mount(); edit("Prepared description");
  expect(button("Áp dụng nháp mô tả").props.disabled).toBe(true);
  expect(commitAssetLineDraft).not.toHaveBeenCalled();
  await click("Lưu nháp");
  expect(saveAssetLineDraft).toHaveBeenCalledExactlyOnceWith("project", "line", {
    field_key: "description", draft_value: "Prepared description", base_value: "Official value", version_token: "7",
  });
  expect(JSON.stringify(root.toJSON())).toContain("Mô tả chính thức: ");
  expect(JSON.stringify(root.toJSON())).toContain("Official value");
  await click("Áp dụng nháp mô tả");
  expect(commitAssetLineDraft).not.toHaveBeenCalled();
  await click("Xác nhận áp dụng mô tả");
  expect(commitAssetLineDraft).toHaveBeenCalledExactlyOnceWith("project", "line", {
    field_keys: ["description"], confirm: true, version_token: "7",
  });
  expect(committed).toHaveBeenCalledOnce();
});
it("does not commit an edited value that differs from its saved preview", async () => {
  await mount(); edit("Saved value"); await click("Lưu nháp"); edit("Unsaved value");
  expect(button("Áp dụng nháp mô tả").props.disabled).toBe(true);
  expect(commitAssetLineDraft).not.toHaveBeenCalled();
});
it("does not claim that metadata-only existing drafts are the official editor value", async () => {
  vi.mocked(fetchProjectDraftState).mockResolvedValue({ items: [{ asset_line_id: "line", changed_fields: ["description"] }] } as any);
  await mount();
  expect(root.root.findByType("textarea").props.value).toBe("Official value");
  expect(JSON.stringify(root.toJSON())).toContain("Dòng có nháp mô tả đã lưu");
  expect(button("Áp dụng nháp mô tả").props.disabled).toBe(true);
});
it("requires fresh review after a conflict or uncertain commit and never automatically posts again", async () => {
  vi.mocked(commitAssetLineDraft).mockRejectedValue({ status: 409 });
  await mount(); edit("New description"); await click("Lưu nháp"); await click("Áp dụng nháp mô tả");
  await click("Xác nhận áp dụng mô tả");
  expect(committed).toHaveBeenCalledOnce(); expect(commitAssetLineDraft).toHaveBeenCalledOnce();
  expect(button("Áp dụng nháp mô tả").props.disabled).toBe(true);
});
it("enforces read-only eligibility and the Unicode character limit", async () => {
  await mount(false); expect(button("Lưu nháp").props.disabled).toBe(true);
  act(() => root.unmount()); await mount(); edit("😀".repeat(5000));
  expect(button("Lưu nháp").props.disabled).toBe(false);
  edit("😀".repeat(5001)); expect(button("Lưu nháp").props.disabled).toBe(true);
});
