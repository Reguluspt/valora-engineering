import { useEffect, useRef, useState } from "react";
import { Button, Dialog, DialogSurface, DialogBody, DialogTitle, DialogContent, DialogActions,
  FluentProvider, webLightTheme, Table, TableHeader, TableBody, TableRow, TableHeaderCell, TableCell } from "@fluentui/react-components";
import { StatusBadge } from "../../common/StatusBadge";
import { MessageBar } from "../../ui/MessageBar";
import { FormField } from "../../ui/FormField";
import { CASE_RESULT_LABELS } from "../../case-overview/caseOverviewPresentation";
import type { QuoteIntent, QuoteItem, QuoteRevision } from "../../../api/supplierQuotes";
import { quoteItemInput } from "../../../api/supplierQuotes";
import type { SupplierQuotesController } from "./useSupplierQuotes";
import { QuoteEditor, ItemFields, validItem, revisionLabels } from "./QuoteEditor";

const statusLabels: Record<string, string> = { draft: "Nháp", confirmed: "Đã xác nhận", withdrawn: "Đã thu hồi", rejected: "Đã loại", superseded: "Đã thay thế" };
const reasonLabels: Record<string, string> = {
  currency_not_current: "Tiền tệ cần kiểm tra lại", source_not_current: "Nguồn không còn hiện hành hoặc không khả dụng",
  supplier_not_current: "Nhà cung cấp không còn hiện hành", upstream_not_current: "Điều kiện danh mục đã thay đổi",
  price_evidence_not_current: "Nguồn giá và chứng cứ cần kiểm tra lại", not_effective: "Chưa đến ngày hiệu lực", quote_expired: "Đã quá hạn hiệu lực hoặc rà soát",
  supplier_identity_ambiguous: "Danh tính nhà cung cấp chưa rõ ràng", line_not_current: "Tài sản đã thay đổi", superseded: "Phiên bản đã được thay thế",
  identity_concern: "Mối lo về danh tính", authenticity_concern: "Mối lo về tính xác thực", integrity_concern: "Mối lo về tính toàn vẹn",
};
const warnings: Record<string, string> = { below_working_price: "Cảnh báo: Giá NCC thấp hơn đơn giá làm việc",
  difference_exceeds_15_percent: "Cảnh báo: Chênh lệch tuyệt đối trên 15%" };
const reasonCopy = (code: string) => reasonLabels[code] || "Điều kiện báo giá cần kiểm tra lại";
type DialogState = { kind: "register"; token: string }
  | { kind: "detail"; revision: QuoteRevision; token: string }
  | { kind: "item"; revision: QuoteRevision; token: string; item?: QuoteItem }
  | { kind: "revise"; revision: QuoteRevision; token: string; mode: "correction" | "replacement" | "negotiation" }
  | { kind: "withdraw" | "reject"; revision: QuoteRevision; target: QuoteRevision; token: string };

export function SupplierQuotesRegion({ quotes, open, onClose, focusRequest }: { quotes: SupplierQuotesController; open: boolean; onClose: () => void; focusRequest: string | null }) {
  const heading = useRef<HTMLHeadingElement>(null), trigger = useRef<HTMLButtonElement | null>(null);
  const [dialog, setDialog] = useState<DialogState | null>(null), [reason, setReason] = useState("");
  const [item, setItem] = useState<QuoteItem>({ line_id: "", quantity: "", unit: "", unit_price: "", source_locator: "" });
  const show = (d: DialogState, button: HTMLButtonElement) => { if (!dialog) trigger.current = button; setReason("");
    if (d.kind === "item") setItem(d.item || { line_id: "", quantity: "", unit: "", unit_price: "", source_locator: "" }); setDialog(d); };
  const closeDialog = () => { setDialog(null); if (trigger.current?.isConnected) trigger.current.focus(); else heading.current?.focus(); };
  useEffect(() => { if (open) heading.current?.focus(); }, [open, focusRequest]);
  useEffect(() => { if (!quotes.snapshot) setDialog(null); }, [quotes.snapshot]);
  if (!open) return null;
  const prep = quotes.snapshot, view = quotes.history;
  const detail = dialog?.kind === "detail" ? view?.items.find(q => q.revision_id === dialog.revision.revision_id) || dialog.revision : null;
  const dialogEnabled = quotes.enabled && dialog?.token === prep?.case_version;
  const title = dialog?.kind === "register" ? "Đăng ký báo giá nháp" : dialog?.kind === "detail" ? "Chi tiết báo giá và phiên bản"
    : dialog?.kind === "item" ? "Ghi nhận dòng báo giá" : dialog?.kind === "revise" ? revisionLabels[dialog.mode]
    : dialog?.kind === "withdraw" ? "Thu hồi báo giá" : "Loại báo giá nháp";
  const confirmation = (revision: QuoteRevision) => prep && <Button appearance="primary" onClick={() => {
    void quotes.submit({ operation: "confirm", quote_id: revision.quote_id, revision_id: revision.revision_id }, prep.case_version).then(done => {
      if (done) { if (dialog) closeDialog(); else heading.current?.focus(); }
    });
  }}>Hoàn tất báo giá NCC này</Button>;
  const actions = (revision: QuoteRevision) => {
    const head = prep?.quotes.find(q => q.quote_id === revision.quote_id && q.revision_id === revision.revision_id);
    const confirmed = view?.items.find(q => q.revision_id === head?.confirmed_revision_id);
    if (!head || !quotes.enabled || !prep) return null;
    return <div className="asset-review-actions">
      {head.can_register_line && <Button onClick={e => show({ kind: "item", revision, token: prep.case_version }, e.currentTarget)}>Thêm dòng báo giá</Button>}
      {head.can_confirm && confirmation(revision)}
      {head.can_revise && Object.entries(revisionLabels).map(([mode, label]) => <Button key={mode}
        onClick={e => show({ kind: "revise", revision, token: prep.case_version, mode: mode as "correction" | "replacement" | "negotiation" }, e.currentTarget)}>{label}</Button>)}
      {head.can_withdraw && <Button disabled={!confirmed} onClick={e => { if (confirmed) show({ kind: "withdraw", revision, target: confirmed, token: prep.case_version }, e.currentTarget); }}>
        Thu hồi báo giá{confirmed ? ` · phiên bản ${confirmed.revision_number}` : " · tải thêm lịch sử"}</Button>}
      {head.can_reject && <Button onClick={e => show({ kind: "reject", revision, target: revision, token: prep.case_version }, e.currentTarget)}>Loại báo giá nháp</Button>}
    </div>;
  };
  return <FluentProvider theme={webLightTheme} className="asset-review-region">
    <section aria-label="Báo giá NCC toàn hồ sơ" aria-busy={quotes.loading || quotes.busy}>
      <div className="asset-review-heading"><h2 ref={heading} tabIndex={-1}>Báo giá NCC · Toàn hồ sơ</h2>
        {prep && <StatusBadge status={prep.result === "COMPLETE" ? "approved" : prep.result === "BLOCKED" ? "blocking" : "review"} label={CASE_RESULT_LABELS[prep.result]} />}
        <Button onClick={onClose}>Đóng không gian báo giá</Button></div>
      {quotes.loading && <p role="status">{prep ? "Đang cập nhật báo giá…" : "Đang tải báo giá…"}</p>}
      {quotes.busy && <p role="status">Đang xử lý thao tác báo giá…</p>}
      {quotes.error && <MessageBar tone="error" title="Chưa xác minh được báo giá" message={quotes.error} detail="Dữ liệu đang hiển thị chưa được kiểm tra lại; thao tác đang khóa." />}
      {quotes.notice && <MessageBar tone={quotes.conflict ? "conflict" : "info"} title="Kết quả thao tác" message={quotes.notice} />}
      {quotes.pending && <MessageBar tone="warning" title="Kết quả chưa xác định" message="Giữ thao tác gốc. Kiểm tra biên nhận trước khi thực hiện thao tác tiếp theo." />}
      {prep?.result === "NOT_AVAILABLE" && <p>Hoàn tất các điều kiện nguồn giá và chứng cứ theo trạng thái hồ sơ trước khi chuẩn bị báo giá.</p>}
      {prep?.result === "BLOCKED" && <MessageBar tone="error" title="Báo giá đang bị chặn" message="Kiểm tra các điều kiện và mối lo đã ghi nhận theo quyền hiện tại." />}
      {prep?.result === "STALE" && <MessageBar tone="warning" title="Báo giá cần xem lại" message="Kiểm tra nguồn, nhà cung cấp và dòng bị ảnh hưởng. Tải trạng thái hiện tại; không tự xác nhận lại." />}
      {prep && !prep.writable && <p>Chỉ đọc. Điều kiện hồ sơ, quyền hoặc phiên làm việc hiện tại chưa cho phép ghi nhận báo giá.</p>}
      {quotes.projection?.next_action?.kind === "NO_AUTHORIZED_DOWNSTREAM_ACTION" && <p role="status">Chưa có hành động tiếp theo được phép.</p>}
      <p>Một nhà cung cấp độc lập có báo giá đã xác nhận và hiện hành cho mỗi dòng đã chốt là đủ. Báo giá bổ sung là tùy chọn; báo giá nháp chưa tạo độ phủ.</p>
      <div className="asset-review-actions">
        {quotes.enabled && prep?.can_register && <Button appearance="primary" onClick={e => show({ kind: "register", token: prep.case_version }, e.currentTarget)}>Đăng ký báo giá nháp</Button>}
        <Button disabled={quotes.busy || quotes.loading} appearance={quotes.pending ? "primary" : "secondary"}
          onClick={() => void (quotes.pending ? quotes.recover() : quotes.refresh())}>{quotes.pending ? "Kiểm tra kết quả thao tác" : "Tải lại báo giá"}</Button>
      </div>
      {prep && <details><summary>Độ phủ chính xác theo danh mục đã chốt</summary><div className="valora-table-shell"><Table className="valora-table" aria-label="Độ phủ báo giá theo tài sản">
        <TableHeader><TableRow>{["Tài sản", "Nhà cung cấp hiện hành đã xác nhận", "Độ phủ"].map(s => <TableHeaderCell key={s}>{s}</TableHeaderCell>)}</TableRow></TableHeader>
        <TableBody>{prep.coverage.map((c, index) => <TableRow key={c.line_id}><TableCell>{index + 1}. {prep.lines.find(l => l.line_id === c.line_id)?.asset_name || "Dòng danh mục đã chốt"}</TableCell>
          <TableCell>{c.supplier_count}</TableCell><TableCell>{c.deficient ? "Cần bổ sung báo giá" : "Đủ độ phủ hiện tại"}</TableCell></TableRow>)}</TableBody>
      </Table></div></details>}
      {prep?.concerns.map((c, i) => <MessageBar key={c.concern_id} tone="warning" title={`Mối lo ${i + 1}`} message={reasonCopy(c.reason_code)} />)}
      {view && !view.items.length && !quotes.error && <p>Chưa có báo giá được đăng ký. Chọn nhà cung cấp phát hành và nguồn báo giá đã lưu để bắt đầu khi hệ thống cho phép.</p>}
      {view && view.items.length > 0 && <div className="valora-table-shell"><Table className="valora-table valora-table--multiline" aria-label="Báo giá và phiên bản">
        <TableHeader><TableRow>{["Báo giá", "Nhà cung cấp phát hành", "Phiên bản", "Trạng thái", "Hiệu lực", "Dòng ánh xạ", "Đóng góp độ phủ", "Cảnh báo", "Thao tác"].map(s => <TableHeaderCell key={s}>{s}</TableHeaderCell>)}</TableRow></TableHeader>
        <TableBody>{view.items.map(q => <TableRow key={q.revision_id}>
          <TableCell>{q.terms.quotation_number || q.title || "Báo giá không có số"}</TableCell><TableCell>{q.supplier.display_name || q.supplier.legal_name}</TableCell>
          <TableCell>{q.revision_number}{q.current_head ? " · Đầu đã xác nhận" : ""}{q.latest_revision ? " · Mới nhất" : ""}</TableCell>
          <TableCell>{statusLabels[q.status] || "Cần kiểm tra"}</TableCell><TableCell>{q.eligible ? "Hiện hành, đủ điều kiện" : q.deficiencies.map(reasonCopy).join("; ") || "Chưa đóng góp độ phủ"}</TableCell>
          <TableCell>{q.items.length}</TableCell><TableCell>{q.coverage_line_ids.length} dòng (máy chủ)</TableCell>
          <TableCell>{[...new Set(q.items.flatMap(i => i.warning_codes))].map(w => <p role="status" key={w}>{warnings[w] || "Cảnh báo báo giá cần xem xét"}</p>)}</TableCell>
          <TableCell><Button onClick={e => show({ kind: "detail", revision: q, token: prep!.case_version }, e.currentTarget)}>Xem báo giá · phiên bản {q.revision_number}</Button>
            {quotes.enabled && prep?.quotes.some(head => head.revision_id === q.revision_id && head.can_confirm) && confirmation(q)}</TableCell>
        </TableRow>)}</TableBody>
      </Table></div>}
      {view?.next_offset !== null && view && <Button disabled={quotes.loading || quotes.busy} onClick={() => void quotes.loadMore("history")}>Tải thêm lịch sử báo giá</Button>}
      <Dialog open={Boolean(dialog)} onOpenChange={(_, d) => { if (!d.open && !quotes.busy) closeDialog(); }}>
        <DialogSurface className="valora-dialog-wide"><DialogBody><DialogTitle>{title}</DialogTitle><DialogContent>
          {dialog?.kind === "register" && <QuoteEditor quotes={quotes} close={closeDialog} />}
          {dialog?.kind === "revise" && <QuoteEditor quotes={quotes} predecessor={dialog.revision} mode={dialog.mode} close={closeDialog} />}
          {dialog?.kind === "detail" && detail && <><p>{detail.title} · {detail.supplier.legal_name} · phiên bản {detail.revision_number}</p>
            <p>{statusLabels[detail.status] || "Cần kiểm tra"}. {detail.predecessor_id ? `Tiếp nối phiên bản ${view?.items.find(q => q.revision_id === detail.predecessor_id)?.revision_number || "trong lịch sử trước"}.` : "Phiên bản đầu tiên."}</p>
            <p>Nguồn đã lưu: phiên bản {detail.source.generation} · {detail.source.byte_length} byte.</p>
            <dl className="asset-context-facts">{Object.entries(detail.terms).filter(([k]) => !["acquisition_method", "comparison_basis"].includes(k)).map(([key, value]) =>
              <div key={key}><dt>{({ quotation_number: "Số báo giá", quotation_number_not_issued_reason: "Lý do không có số", quote_date: "Ngày báo giá", effective_at: "Ngày hiệu lực", expires_at: "Ngày hết hiệu lực", review_due_at: "Hạn rà soát", currency: "Tiền tệ", tax: "Thuế", delivery: "Giao hàng", condition: "Tình trạng/điều kiện", warranty: "Bảo hành", payment: "Thanh toán", limitations: "Giới hạn", source_locator: "Vị trí nguồn" } as Record<string, string>)[key]}</dt><dd>{value || "Không ghi nhận"}</dd></div>)}</dl>
            <p>Cơ sở so sánh: {detail.terms.comparison_basis === "same_working_unit_basis" ? "Cùng cơ sở đơn vị làm việc" : "Chưa đánh giá cùng cơ sở"}.</p>
            <Table className="valora-table" aria-label="Các dòng báo giá đã ánh xạ"><TableHeader><TableRow>{["Tài sản", "Số lượng", "Đơn vị", "Đơn giá NCC", "Vị trí nguồn", "Thao tác"].map(label => <TableHeaderCell key={label}>{label}</TableHeaderCell>)}</TableRow></TableHeader>
              <TableBody>{detail.items.map(i => <TableRow key={i.item_id}><TableCell>{prep?.lines.find(l => l.line_id === i.line_id)?.asset_name || "Dòng đã chốt"}</TableCell>
                <TableCell>{i.quantity}</TableCell><TableCell>{i.unit}</TableCell><TableCell>{i.unit_price}</TableCell><TableCell>{i.source_locator}</TableCell>
                <TableCell>{quotes.enabled && prep?.quotes.some(q => q.revision_id === detail.revision_id && q.can_register_line) && <Button
                  onClick={e => show({ kind: "item", revision: detail, token: prep.case_version, item: quoteItemInput(i) }, e.currentTarget)}>Sửa dòng nháp</Button>}</TableCell></TableRow>)}</TableBody></Table>
            <p>Thao tác Hoàn tất báo giá NCC này xác nhận đúng phiên bản đang hiển thị.</p>{dialog.token === prep?.case_version && actions(detail)}</>}
          {dialog?.kind === "item" && <form onSubmit={e => { e.preventDefault(); if (!dialogEnabled || !validItem(item)) return;
            void quotes.submit({ operation: "register-line", quote_id: dialog.revision.quote_id, revision_id: dialog.revision.revision_id, item }, dialog.token).then(done => { if (done) closeDialog(); }); }}>
            <ItemFields item={item} quotes={quotes} onChange={setItem} />
            <div className="asset-review-actions"><Button onClick={closeDialog}>Hủy</Button><Button type="submit" appearance="primary" disabled={!dialogEnabled || !validItem(item)}>Ghi nhận dòng báo giá</Button></div></form>}
          {(dialog?.kind === "withdraw" || dialog?.kind === "reject") && <>
            <p>{dialog.target.terms.quotation_number || dialog.target.title} · phiên bản {dialog.target.revision_number}. {statusLabels[dialog.target.status]}.</p>
            <p>{dialog.kind === "withdraw" ? "Thu hồi được ghi vào lịch sử. Độ phủ hiện tại sẽ được máy chủ kiểm tra lại; không tự quay về phiên bản cũ." : "Loại phiên bản chưa xác nhận và giữ lịch sử báo giá."}</p>
            <FormField label="Lý do" value={reason} onChange={setReason} multiline error={[...reason.trim()].length > 2000 ? "Tối đa 2000 ký tự." : undefined} />
            {!dialogEnabled && <p role="alert">Ngữ cảnh đã thay đổi. Đóng biểu mẫu và kiểm tra trạng thái hiện tại.</p>}
          </>}
          {quotes.notice && <p role="status">{quotes.notice}</p>}{quotes.error && <p role="alert">{quotes.error}</p>}
        </DialogContent>
          {dialog?.kind !== "register" && dialog?.kind !== "revise" && dialog?.kind !== "item" && <DialogActions><Button onClick={closeDialog}>Đóng</Button>
            {(dialog?.kind === "withdraw" || dialog?.kind === "reject") && <Button appearance="primary" disabled={!dialogEnabled || !reason.trim() || [...reason.trim()].length > 2000}
              onClick={() => { if (!dialog) return; const base = { quote_id: dialog.revision.quote_id, revision_id: dialog.revision.revision_id, reason_note: reason.trim() };
                const intent: QuoteIntent = dialog.kind === "withdraw" ? { ...base, operation: "withdraw", target_revision_id: dialog.target.revision_id } : { ...base, operation: "reject" };
                void quotes.submit(intent, dialog.token).then(done => { if (done) closeDialog(); }); }}>{dialog.kind === "withdraw" ? "Thu hồi báo giá" : "Loại báo giá nháp"}</Button>}
          </DialogActions>}
        </DialogBody></DialogSurface>
      </Dialog>
    </section>
  </FluentProvider>;
}
