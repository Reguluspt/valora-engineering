import React from "react";
import { act, create, type ReactTestRenderer } from "react-test-renderer";
import { afterEach, expect, it, vi } from "vitest";
import { SupplierQuotesRegion } from "../SupplierQuotesRegion";
import { exactDecimal } from "../QuoteEditor";
import type { SupplierQuotesController } from "../useSupplierQuotes";
import { prep, quote, state, token, id, revision } from "./fixtures";

vi.mock("@fluentui/react-components", () => {
  const element = (tag: string) => (props: any) => React.createElement(tag, props, props.children);
  return { Button: element("button"), FluentProvider: element("div"), webLightTheme: {},
    Table: element("table"), TableHeader: element("thead"), TableBody: element("tbody"), TableRow: element("tr"),
    TableHeaderCell: element("th"), TableCell: element("td"), Dialog: ({ open, children }: any) => open ? children : null,
    DialogSurface: element("section"), DialogBody: element("div"), DialogTitle: element("h2"), DialogContent: element("div"),
    DialogActions: element("div"), Field: element("label"), Input: element("input"), Textarea: element("textarea"), Select: element("select") };
});
const roots: ReactTestRenderer[] = [];
afterEach(() => roots.splice(0).forEach(root => act(() => root.unmount())));
const text = (node: any): string => typeof node === "string" || typeof node === "number" ? String(node) : Array.isArray(node) ? node.map(text).join("") : node?.props ? text(node.props.children) : "";
const mount = (changes: Partial<SupplierQuotesController> = {}) => {
  const quotes = { snapshot: prep, history: { items: [quote], case_version: token, offset: 0, limit: 50, next_offset: null },
    projection: state, enabled: true, loading: false, busy: false, error: "", notice: "", pending: null,
    submit: vi.fn().mockResolvedValue(false), refresh: vi.fn(), recover: vi.fn(), loadMore: vi.fn(), ...changes } as unknown as SupplierQuotesController;
  let root!: ReactTestRenderer;
  act(() => { root = create(<SupplierQuotesRegion quotes={quotes} open onClose={vi.fn()} focusRequest={null} />); });
  roots.push(root);
  return { root, quotes, buttons: (label: string) => root.root.findAllByType("button").filter(b => text(b) === label) };
};
it("confirmation activates the exact displayed revision once without opening a second step", () => {
  const m = mount();
  act(() => m.buttons("Hoàn tất báo giá NCC này")[0].props.onClick());
  expect(m.quotes.submit).toHaveBeenCalledExactlyOnceWith({ operation: "confirm", quote_id: id, revision_id: revision }, token);
  expect(m.root.root.findAllByType("input").filter(i => i.props.type === "checkbox")).toHaveLength(0);
  expect(m.root.root.findAllByType("section")).toHaveLength(1);
});
it("warnings stay visible while server confirmation remains permitted; draft coverage stays zero", () => {
  const m = mount({ history: { items: [{ ...quote, items: quote.items.map(i => ({ ...i, warning_codes: ["below_working_price", "difference_exceeds_15_percent"] })) }],
    case_version: token, offset: 0, limit: 50, next_offset: null } });
  const content = JSON.stringify(m.root.toJSON());
  expect(content).toContain("Giá NCC thấp hơn đơn giá làm việc"); expect(content).toContain("Chênh lệch tuyệt đối trên 15%");
  expect(m.root.root.findAllByType("td").some(cell => text(cell) === "0 dòng (máy chủ)")).toBe(true);
  expect(m.buttons("Hoàn tất báo giá NCC này")).toHaveLength(1);
});
it.each(["NOT_AVAILABLE", "BLOCKED", "STALE", "INCOMPLETE", "COMPLETE"] as const)("presents server %s without promoting coverage or enabling unauthorized writes", result => {
  const m = mount({ snapshot: { ...prep, result, writable: false }, enabled: false });
  expect(m.quotes.snapshot?.result).toBe(result); expect(m.buttons("Hoàn tất báo giá NCC này")).toHaveLength(0);
  expect(m.buttons("Đăng ký báo giá nháp")).toHaveLength(0);
});
it("unknown outcome exposes receipt reconciliation while all new quotation commands remain unavailable", () => {
  const m = mount({ pending: { commandId: id, contract: "supplier-quote-confirmation-v1" }, enabled: false });
  act(() => m.buttons("Kiểm tra kết quả thao tác")[0].props.onClick());
  expect(m.quotes.recover).toHaveBeenCalledOnce(); expect(m.quotes.submit).not.toHaveBeenCalled();
});
it.each(["0", "1e2", "-1", "1,2", "01", "0.0000000001", "1234567890123456789"])("rejects unsafe Decimal text %s before transport", value => {
  expect(exactDecimal(value)).toBe(false);
});
it("accepts exact high precision price strings", () => expect(exactDecimal("123456789012345678.12345678")).toBe(true));
