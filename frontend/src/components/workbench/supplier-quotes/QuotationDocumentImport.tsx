import { useEffect, useRef, useState } from "react";
import { Button, Dialog, DialogSurface, DialogBody, DialogTitle, DialogContent, DialogActions, Field, Textarea, makeStyles, tokens } from "@fluentui/react-components";
import { MessageBar } from "../../ui/MessageBar";
import type { QuotationDocumentImportController } from "./useQuotationDocumentImport";

const useStyles = makeStyles({
  details: { overflowWrap: "anywhere", color: tokens.colorNeutralForeground2 },
  preview: { width: "100%" },
});

export function QuotationDocumentImport({ controller: c }: { controller: QuotationDocumentImportController }) {
  const styles = useStyles(), trigger = useRef<HTMLButtonElement>(null), chooser = useRef<HTMLInputElement>(null), returnFocus = useRef(false);
  const [open, setOpen] = useState(false);
  const close = () => { if (!c.busy) { setOpen(false); returnFocus.current = true; void c.select(null); } };
  useEffect(() => {
    if (c.status?.outcome === "finalized") { setOpen(false); returnFocus.current = true; }
  }, [c.status?.receipt_id]);
  useEffect(() => {
    if (!open && !c.loading && !c.busy && returnFocus.current) { returnFocus.current = false; trigger.current?.focus(); }
  }, [open, c.loading, c.busy]);
  if (!c.context && !c.loading && !c.error && !c.pending) return null;
  return <section aria-label="Nhập nguyên bản báo giá TXT" aria-busy={c.loading || c.busy}>
    <Button ref={trigger} disabled={c.loading || c.busy} onClick={() => { setOpen(true); void c.refresh(); }}>Nhập tài liệu báo giá TXT</Button>
    {c.loading && <p role="status">Đang kiểm tra quyền nhập tài liệu…</p>}
    {c.error && <MessageBar title="Trạng thái nhập tài liệu" message={c.error} tone="warning" />}
    {c.status?.outcome === "finalized" && <MessageBar title="Đã lưu nguyên bản tài liệu" tone={c.status.source?.available ? "success" : "warning"}
      message={c.status.source?.available ? "Nguồn đã được máy chủ xác minh. Chủ động chọn nguồn khi đăng ký báo giá."
        : "Biên nhận đã được ghi nhận; nguồn hiện chưa khả dụng. Chưa thể chọn nguồn để đăng ký báo giá."} />}
    {c.pending && <MessageBar title={c.status?.outcome === "pending" ? "Lần nhập đang chờ hoàn tất" : "Kết quả chưa xác định"}
      message="Giữ thao tác gốc. Kiểm tra kết quả trước; khôi phục cần chọn lại đúng tệp và xác nhận."
      tone="warning" actionLabel="Kiểm tra kết quả" onAction={() => void c.reconcile()} />}
    <Dialog open={open} onOpenChange={(_, data) => { if (!data.open) close(); }}>
      <DialogSurface className="valora-dialog-wide"><DialogBody>
        <DialogTitle>Nhập tài liệu báo giá TXT</DialogTitle>
        <DialogContent>
          {c.error && <MessageBar title="Trạng thái nhập tài liệu" message={c.error} tone="warning" />}
          {c.context && <p className={styles.details}>Hồ sơ: <strong>{c.context.project_code} · {c.context.project_name}</strong></p>}
          <p>Lưu nguyên bản tài liệu vào hồ sơ này. Việc nhập tài liệu chưa xác nhận nội dung báo giá NCC.</p>
          {!c.context?.can_import && !c.pending && !c.loading && <MessageBar title="Chưa được nhập tài liệu"
            message="Quyền hoặc trạng thái hồ sơ hiện tại chưa cho phép nhập. Kiểm tra lại hồ sơ." tone="warning" />}
          <Field label={c.pending ? "Chọn lại đúng tệp gốc để khôi phục" : "Một tệp UTF-8 .txt, từ 1 đến 1.048.576 byte"}>
            <Button disabled={c.busy || c.loading || (!c.pending && !c.context?.can_import)} onClick={() => chooser.current?.click()}>
              {c.selection ? "Chọn tệp khác" : "Chọn tệp TXT"}</Button>
            <input ref={chooser} hidden type="file" accept=".txt,text/plain" disabled={c.busy || c.loading || (!c.pending && !c.context?.can_import)}
              onChange={event => { const file = event.currentTarget.files?.[0] || null;
                event.currentTarget.value = ""; void c.select(file); }} />
          </Field>
          {c.selection && <>
            <dl className={styles.details}><dt>Tệp gốc</dt><dd>{c.selection.filename}</dd>
              <dt>Kích thước</dt><dd>{c.selection.file.size} byte</dd><dt>SHA-256</dt><dd>{c.selection.sha256}</dd></dl>
            <Field label="Xem trước văn bản thuần (tối đa 4.096 ký tự Unicode)">
              <Textarea className={styles.preview} rows={8} value={c.selection.preview} readOnly />
            </Field>
            {c.selection.truncated && <p role="status">Bản xem trước đã được rút gọn. Tệp gốc được lưu đủ nguyên byte.</p>}
          </>}
          {c.busy && <p role="status">Đang xử lý lần nhập; đóng cửa sổ không chứng minh thao tác đã hủy.</p>}
        </DialogContent>
        <DialogActions>
          <Button disabled={c.busy} onClick={close}>Đóng</Button>
          {c.pending && <Button disabled={c.busy} onClick={() => void c.reconcile()}>Kiểm tra kết quả</Button>}
          <Button appearance="primary" disabled={!c.enabled} onClick={() => void c.submit()}>
            {c.pending ? "Khôi phục lần nhập này" : "Xác nhận nhập tài liệu"}</Button>
        </DialogActions>
      </DialogBody></DialogSurface>
    </Dialog>
  </section>;
}
