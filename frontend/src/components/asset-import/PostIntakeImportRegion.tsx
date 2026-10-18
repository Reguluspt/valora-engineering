import { useEffect, useRef } from "react";
import { Button, Dialog, DialogSurface, DialogBody, DialogTitle, DialogContent, DialogActions,
  FluentProvider, webLightTheme, makeStyles, tokens, Table, TableHeader, TableBody,
  TableRow, TableHeaderCell, TableCell } from "@fluentui/react-components";
import { LoadingState } from "../common/LoadingState";
import { EmptyState } from "../common/EmptyState";
import { RbacLockNotice } from "../common/RbacLockNotice";
import { MessageBar } from "../ui/MessageBar";
import { PAGE_SIZE } from "./postIntakeImportModel";
import { usePostIntakeImport, type PostIntakeImportOptions } from "./usePostIntakeImport";

const useStyles = makeStyles({
  region: { padding: tokens.spacingHorizontalL, borderRadius: tokens.borderRadiusMedium,
    backgroundColor: tokens.colorNeutralBackground1, border: `${tokens.strokeWidthThin} solid ${tokens.colorNeutralStroke2}` },
  actions: { display: "flex", flexWrap: "wrap", alignItems: "center", gap: tokens.spacingHorizontalS,
    marginTop: tokens.spacingVerticalM, marginBottom: tokens.spacingVerticalM },
  table: { overflowX: "auto", maxWidth: "100%" },
  details: { overflowWrap: "anywhere", color: tokens.colorNeutralForeground2 },
});
const statuses = { pending: "Chưa kiểm tra", valid: "Hợp lệ", invalid: "Không hợp lệ", warning: "Cảnh báo" };
const fields: Record<string, string> = { proposed_asset_name: "Tên tài sản", proposed_quantity: "Số lượng" };

export function PostIntakeImportRegion(props: PostIntakeImportOptions & { focusRequest: number }) {
  const flow = usePostIntakeImport(props);
  const styles = useStyles();
  const heading = useRef<HTMLHeadingElement>(null);
  const applyTrigger = useRef<HTMLButtonElement>(null);
  const wasOpen = useRef(false);
  const snapshot = flow.snapshot, dialog = flow.confirmation;
  useEffect(() => { if (props.focusRequest) heading.current?.focus(); }, [props.focusRequest]);
  useEffect(() => {
    if (wasOpen.current && !dialog) {
      if (applyTrigger.current && !applyTrigger.current.disabled) applyTrigger.current.focus();
      else heading.current?.focus();
    }
    wasOpen.current = Boolean(dialog);
  }, [dialog]);

  return <FluentProvider theme={webLightTheme} className={styles.region}>
    <section aria-labelledby="post-intake-import-title" aria-busy={flow.loading || flow.busy}>
      <h2 id="post-intake-import-title" ref={heading} tabIndex={-1}>Danh mục nhập sau tiếp nhận</h2>
      <p>Kiểm tra danh mục đã được hồ sơ chọn, rồi xác nhận riêng để tạo danh mục tài sản chính thức.</p>
      {!props.canEdit && <RbacLockNotice permission="workbench:edit" />}
      {flow.loading && <LoadingState scope="section" message="Đang kiểm tra trạng thái hồ sơ và danh mục được chọn." />}
      {flow.error && <MessageBar tone="error" title="Chưa thể thực hiện thao tác" message={flow.error} />}
      {flow.notice && <MessageBar tone={flow.conflict ? "conflict" : "info"} title="Kết quả thao tác" message={flow.notice} />}
      {flow.pending && <MessageBar tone="warning" title="Kết quả chưa xác định"
        message="Thao tác đang khóa. Chỉ đọc lại dữ liệu để đối soát; không gửi lại yêu cầu áp dụng. Nếu chưa xác định được kết quả, hãy liên hệ người phụ trách hồ sơ." />}
      {flow.proven && <MessageBar tone="success" title="Danh mục đã được áp dụng"
        message="Tiếp tục theo hành động tiếp theo của hồ sơ để mở Rà soát tài sản trong Bàn làm việc. Từng tài sản vẫn cần được kiểm tra và chấp nhận riêng." />}
      {snapshot && <>
        <h3>{snapshot.batch.source_filename}</h3>
        <p>Trang tính: {snapshot.batch.source_sheet_name || "Chưa có tên"} · Tổng {snapshot.batch.total_rows} dòng ·
          Hợp lệ: {snapshot.batch.valid_rows} · Không hợp lệ: {snapshot.batch.invalid_rows} · Cảnh báo: {snapshot.batch.warning_rows}</p>
        <details className={styles.details}><summary>Nguồn danh mục được hồ sơ chọn</summary>
          <p>Lần nhập: {snapshot.target.batch_id}</p><p>Tiếp nhận: {snapshot.target.official_intake_commit_id}</p>
          <p>Kết quả sơ bộ: {snapshot.target.result_id}</p><p>Lần chuẩn bị dữ liệu: {snapshot.target.staging_usage_id}</p>
        </details>
        {!snapshot.rows.total ? <EmptyState title="Danh mục chưa có dòng dữ liệu" message="Chưa đủ điều kiện áp dụng danh mục chính thức." /> :
          <div className={styles.table} role="region" aria-label="Dòng dữ liệu nhập" tabIndex={0}>
            <Table aria-label="Danh mục đã chọn" size="small"><TableHeader><TableRow>
              {["Dòng nguồn", "Tên tài sản", "Số lượng", "Đơn vị", "Kết quả kiểm tra", "Điểm cần xem lại"].map(label => <TableHeaderCell key={label}>{label}</TableHeaderCell>)}
            </TableRow></TableHeader><TableBody>{snapshot.rows.items.map(row => <TableRow key={row.id}>
              <TableCell>{row.source_row_number}</TableCell><TableCell>{row.proposed_asset_name || "Chưa có tên"}</TableCell>
              <TableCell>{row.proposed_quantity ?? ""}</TableCell><TableCell>{row.proposed_unit ?? ""}</TableCell>
              <TableCell>{statuses[row.validation_status]}</TableCell>
              <TableCell>{[...row.validation_errors, ...row.validation_warnings].map((finding, i) =>
                <div key={i}>{fields[finding.field || ""] ? `${fields[finding.field!]}: ` : ""}{finding.message || "Dữ liệu cần kiểm tra lại."}</div>)}</TableCell>
            </TableRow>)}</TableBody></Table>
          </div>}
        <div className={styles.actions} aria-label="Phân trang danh mục nhập">
          <Button disabled={flow.loading || flow.busy || snapshot.rows.offset === 0} onClick={() => void flow.refresh(snapshot.rows.offset - PAGE_SIZE)}>Trang trước</Button>
          <span>{snapshot.rows.total ? `${snapshot.rows.offset + 1}–${snapshot.rows.offset + snapshot.rows.items.length}` : "0"} / {snapshot.rows.total} dòng</span>
          <Button disabled={flow.loading || flow.busy || snapshot.rows.offset + snapshot.rows.items.length >= snapshot.rows.total}
            onClick={() => void flow.refresh(snapshot.rows.offset + PAGE_SIZE)}>Trang sau</Button>
        </div>
      </>}
      <div className={styles.actions}>
        {flow.canValidate && <Button appearance="primary" onClick={() => void flow.submit("validate")}>Kiểm tra danh mục nhập</Button>}
        {flow.canApply && <Button appearance="primary" ref={applyTrigger} onClick={() => void flow.openConfirmation()}>Áp dụng danh mục chính thức</Button>}
        <Button disabled={flow.loading || flow.busy} onClick={() => void flow.refresh()}>{flow.pending ? "Kiểm tra kết quả thao tác" : "Tải lại danh mục"}</Button>
        {flow.busy && <span role="status">Đang xử lý thao tác…</span>}
      </div>
      <Dialog open={Boolean(dialog)} onOpenChange={(_, data) => { if (!data.open) flow.closeConfirmation(); }}>
        <DialogSurface><DialogBody><DialogTitle>Xác nhận áp dụng danh mục chính thức</DialogTitle>
          <DialogContent>{dialog && <>
            <p>{dialog.batch.source_filename} · Trang tính {dialog.batch.source_sheet_name || "chưa có tên"} · {dialog.batch.total_rows} dòng.</p>
            <p>Máy chủ sẽ tạo danh mục tài sản chính thức ban đầu từ đúng danh mục này. Sau đó, từng tài sản cần được kiểm tra và chấp nhận riêng.</p>
            <p>Hãy xác nhận khi bạn đã rà soát nguồn và các dòng được chọn.</p>
          </>}</DialogContent>
          <DialogActions><Button onClick={flow.closeConfirmation}>Hủy</Button>
            <Button appearance="primary" disabled={!dialog || flow.busy} onClick={() => void flow.submit("apply")}>Xác nhận áp dụng</Button>
          </DialogActions>
        </DialogBody></DialogSurface>
      </Dialog>
    </section>
  </FluentProvider>;
}
