import { useState } from "react";
import { Button } from "@fluentui/react-components";
import { FormField, SelectField } from "../../ui/FormField";
import { MessageBar } from "../../ui/MessageBar";
import { quoteItemInput, type QuoteTerms, type QuoteItem, type QuoteRevision, type QuoteIntent } from "../../../api/supplierQuotes";
import type { SupplierQuotesController } from "./useSupplierQuotes";

export const revisionLabels = { correction: "Sửa bằng phiên bản mới", replacement: "Thay thế bằng phiên bản mới", negotiation: "Phiên bản thương lượng" };
export const exactDecimal = (value: string) => /^(?:0|[1-9]\d*)(?:\.\d{1,8})?$/.test(value) && /[1-9]/.test(value) && value.split(".")[0].length <= 18;
const localDate = (value: string) => { const d = new Date(value); return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16); };
const termLabels = { tax: "Thuế", delivery: "Giao hàng", condition: "Tình trạng/điều kiện", warranty: "Bảo hành", payment: "Thanh toán", limitations: "Giới hạn", source_locator: "Vị trí nguồn" } as const;
const emptyTerms: QuoteTerms = { quotation_number: null, quotation_number_not_issued_reason: null, quote_date: "", effective_at: "",
  expires_at: null, review_due_at: "", currency: "VND", tax: "", delivery: "", condition: "", warranty: "", payment: "", limitations: "", source_locator: "",
  acquisition_method: "already_retained_document_reference", comparison_basis: "unassessed" };
export function ItemFields({ item, onChange, quotes }: { item: QuoteItem; onChange: (item: QuoteItem) => void; quotes: SupplierQuotesController }) {
  const line = quotes.snapshot?.lines.find(l => l.line_id === item.line_id);
  return <div className="valora-form-grid">
    <SelectField label="Tài sản trong danh mục đã chốt" value={item.line_id} options={(quotes.snapshot?.lines || []).map((l, index) =>
      ({ value: l.line_id, label: `${index + 1}. ${l.asset_name} · ${l.quantity} ${l.unit || "Chưa có đơn vị"} · ${l.description || ""}` }))}
      onChange={line_id => { const l = quotes.snapshot?.lines.find(l => l.line_id === line_id); onChange({ ...item, line_id, quantity: l?.quantity || "", unit: l?.unit || "" }); }} />
    <FormField label="Số lượng báo giá" value={item.quantity} onChange={quantity => onChange({ ...item, quantity })}
      error={item.quantity && !exactDecimal(item.quantity) ? "Nhập số thập phân dương, tối đa 8 chữ số sau dấu chấm." : undefined} />
    <FormField label="Đơn vị báo giá" value={item.unit} onChange={unit => onChange({ ...item, unit })} />
    <FormField label="Đơn giá NCC" value={item.unit_price} onChange={unit_price => onChange({ ...item, unit_price })}
      error={item.unit_price && !exactDecimal(item.unit_price) ? "Nhập số thập phân dương, tối đa 8 chữ số sau dấu chấm." : undefined} />
    <FormField label="Vị trí dòng trong nguồn" value={item.source_locator} onChange={source_locator => onChange({ ...item, source_locator })} />
    {line && <p>Danh mục chính thức: {line.quantity} {line.unit || "Chưa có đơn vị"}. Máy chủ kiểm tra ánh xạ chính xác.</p>}
  </div>;
}
export const validItem = (item: QuoteItem) => Boolean(item.line_id && item.unit.trim() && exactDecimal(item.quantity) && exactDecimal(item.unit_price) && item.source_locator.trim());
export function QuoteEditor({ quotes, predecessor, mode, close }: { quotes: SupplierQuotesController; predecessor?: QuoteRevision;
  mode?: "correction" | "replacement" | "negotiation"; close: () => void }) {
  const [token] = useState(quotes.snapshot?.case_version || "");
  const [supplierId, setSupplierId] = useState(predecessor?.supplier_id || "");
  const [sourceId, setSourceId] = useState(predecessor?.source.revision_id || "");
  const [terms, setTerms] = useState<QuoteTerms>(predecessor ? { ...predecessor.terms, effective_at: localDate(predecessor.terms.effective_at),
    expires_at: predecessor.terms.expires_at ? localDate(predecessor.terms.expires_at) : null, review_due_at: localDate(predecessor.terms.review_due_at) } : emptyTerms);
  const [items, setItems] = useState<QuoteItem[]>(predecessor?.items.map(quoteItemInput) || []);
  const [reason, setReason] = useState(""); const [resolutions, setResolutions] = useState<string[]>([]), [evidence, setEvidence] = useState("");
  const sourceOptions = (quotes.sources?.items || []).filter(s => predecessor ? s.quote_id === predecessor.quote_id : !quotes.snapshot?.quotes.some(q => q.quote_id === s.quote_id));
  const chosenSource = sourceOptions.find(s => s.source_revision_id === sourceId);
  const chosenSupplier = quotes.suppliers?.items.find(s => s.supplier_id === supplierId);
  const allowed = quotes.enabled && token === quotes.snapshot?.case_version;
  const patch = <K extends keyof QuoteTerms>(key: K, value: QuoteTerms[K]) => setTerms(t => ({ ...t, [key]: value }));
  const concerns = (quotes.snapshot?.concerns || []).filter(c => c.quote_id === predecessor?.quote_id);
  const valid = allowed && chosenSource?.available && chosenSupplier && terms.quote_date && terms.effective_at && terms.review_due_at &&
    (terms.quotation_number?.trim() || terms.quotation_number_not_issued_reason?.trim()) && Object.keys(termLabels).every(k => terms[k as keyof typeof termLabels].trim()) &&
    (!mode || reason.trim() && items.length && items.every(validItem)) && (!resolutions.length || evidence.trim());
  const addItem = () => setItems(i => [...i, { line_id: "", quantity: "", unit: "", unit_price: "", source_locator: "" }]);
  return <form onSubmit={e => { e.preventDefault(); if (!valid || !chosenSource) return;
    const utcTerms = { ...terms, quotation_number: terms.quotation_number?.trim() || null,
      quotation_number_not_issued_reason: terms.quotation_number?.trim() ? null : terms.quotation_number_not_issued_reason?.trim() || null,
      effective_at: new Date(terms.effective_at).toISOString(), expires_at: terms.expires_at ? new Date(terms.expires_at).toISOString() : null,
      review_due_at: new Date(terms.review_due_at).toISOString() };
    const common = { quote_id: chosenSource.quote_id, supplier_id: supplierId, source_revision_id: sourceId, terms: utcTerms };
    const intent: QuoteIntent = mode && predecessor ? { ...common, operation: "revise", revision_id: predecessor.revision_id, revision_reason: mode,
      reason_note: reason.trim(), items, resolves_concern_ids: resolutions, resolution_evidence: resolutions.length ? evidence.trim() : null }
      : { ...common, operation: "register" };
    void quotes.submit(intent, token).then(done => { if (done) close(); });
  }}>
    {!allowed && <MessageBar tone="conflict" title="Thao tác đang khóa" message="Ngữ cảnh đã thay đổi hoặc chưa được kiểm tra. Đóng biểu mẫu và xem trạng thái hiện tại." />}
    {predecessor && <p>Phiên bản trước: {predecessor.terms.quotation_number || predecessor.title} · phiên bản {predecessor.revision_number}. Kết quả ảnh hưởng do máy chủ xác định sau khi ghi nhận.</p>}
    <div className="valora-form-grid">
      <SelectField label="Nhà cung cấp phát hành báo giá" value={supplierId} onChange={setSupplierId} disabled={Boolean(mode && mode !== "correction")}
        options={(quotes.suppliers?.items || []).map(s => ({ value: s.supplier_id, label: s.display_name ? `${s.display_name} · ${s.legal_name}` : s.legal_name }))} />
      <SelectField label="Nguồn báo giá đã lưu" value={sourceId} onChange={setSourceId}
        options={sourceOptions.map((s, index) => ({ value: s.source_revision_id, label: `${index + 1}. ${s.title} · ${s.document_type} · phiên bản ${s.revision_number} · ${s.byte_length} byte${s.available ? "" : " · Không khả dụng"}`, disabled: !s.available }))} />
      <FormField label="Số báo giá" value={terms.quotation_number || ""} required={false} onChange={v => patch("quotation_number", v || null)} />
      {!terms.quotation_number?.trim() && <FormField label="Lý do không có số báo giá" value={terms.quotation_number_not_issued_reason || ""} onChange={v => patch("quotation_number_not_issued_reason", v || null)} />}
      <FormField label="Ngày báo giá" type="date" value={terms.quote_date} onChange={v => patch("quote_date", v)} />
      <FormField label="Ngày hiệu lực (giờ địa phương)" type="datetime-local" value={terms.effective_at} onChange={v => patch("effective_at", v)} />
      <FormField label="Ngày hết hiệu lực (giờ địa phương)" type="datetime-local" value={terms.expires_at || ""} required={false} onChange={v => patch("expires_at", v || null)} />
      <FormField label="Hạn rà soát (giờ địa phương)" type="datetime-local" value={terms.review_due_at} onChange={v => patch("review_due_at", v)} />
      <FormField label="Tiền tệ (3 chữ hoa)" value={terms.currency} onChange={v => patch("currency", v)} />
      {Object.entries(termLabels).map(([key, label]) => <FormField key={key} label={label} value={terms[key as keyof typeof termLabels]} onChange={v => patch(key as keyof typeof termLabels, v)} />)}
      <SelectField label="Cơ sở so sánh" value={terms.comparison_basis} onChange={v => patch("comparison_basis", v as QuoteTerms["comparison_basis"])}
        options={[{ value: "unassessed", label: "Chưa đánh giá cùng cơ sở" }, { value: "same_working_unit_basis", label: "Cùng cơ sở đơn vị làm việc" }]} />
      {mode && <FormField label="Lý do tạo phiên bản mới" value={reason} onChange={setReason} multiline />}
    </div>
    {quotes.suppliers?.next_offset !== null && <Button disabled={quotes.loading} onClick={() => void quotes.loadMore("suppliers")}>Tải thêm nhà cung cấp</Button>}
    {quotes.sources?.next_offset !== null && <Button disabled={quotes.loading} onClick={() => void quotes.loadMore("sources")}>Tải thêm nguồn đã lưu</Button>}
    {!chosenSource?.available && <p>Nguồn đã chọn chưa khả dụng. Kiểm tra nguồn hoặc chủ động chọn nguồn được phép; hệ thống không tự thay nguồn.</p>}
    {mode && <><h3>Ánh xạ chính xác của phiên bản mới</h3>{items.map((item, index) => <fieldset key={index}><legend>Dòng báo giá {index + 1}</legend>
      <ItemFields item={item} quotes={quotes} onChange={next => setItems(all => all.map((i, n) => n === index ? next : i))} />
      <Button onClick={() => setItems(all => all.filter((_, n) => n !== index))}>Bỏ dòng khỏi phiên bản mới</Button>
    </fieldset>)}<Button onClick={addItem}>Thêm ánh xạ chính xác</Button></>}
    {mode && concerns.length > 0 && <><p>Mối lo đã ghi nhận: chọn đúng mối lo đã xử lý nếu phiên bản này giải quyết nó.</p>
      {concerns.map((c, index) => <SelectField key={c.concern_id} label={`Xử lý mối lo đã ghi nhận ${index + 1}`} required={false}
        value={resolutions.includes(c.concern_id) ? "resolved" : ""} options={[{ value: "resolved", label: "Phiên bản này giải quyết mối lo" }]}
        onChange={v => setResolutions(ids => v ? [...ids.filter(id => id !== c.concern_id), c.concern_id] : ids.filter(id => id !== c.concern_id))} />)}
      {resolutions.length > 0 && <FormField label="Căn cứ xử lý mối lo" value={evidence} onChange={setEvidence} multiline />}</>}
    <div className="asset-review-actions"><Button onClick={close}>Hủy</Button><Button type="submit" appearance="primary" disabled={!valid}>
      {mode ? revisionLabels[mode] : "Đăng ký báo giá nháp"}</Button></div>
  </form>;
}
