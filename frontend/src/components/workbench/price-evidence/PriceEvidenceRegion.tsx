import { useEffect, useRef, useState } from "react";
import { Button, Dialog, DialogSurface, DialogBody, DialogTitle, DialogContent, DialogActions, FluentProvider, webLightTheme } from "@fluentui/react-components";
import { StatusBadge } from "../../common/StatusBadge";
import { CASE_RESULT_LABELS } from "../../case-overview/caseOverviewPresentation";
import type { EvidencePreparation } from "../../../api/priceEvidence";
import type { PriceEvidenceController } from "./usePriceEvidence";
import { EvidenceField } from "./EvidenceFields";

export function PriceEvidenceRegion({ evidence }: { evidence: PriceEvidenceController }) {
  const [dialog, setDialog] = useState<{ operation: "confirm" | "withdraw-confirmation"; snapshot: EvidencePreparation } | null>(null);
  const [reason, setReason] = useState("");
  const trigger = useRef<HTMLButtonElement | null>(null);
  const close = () => { setDialog(null); setReason(""); trigger.current?.focus(); };
  useEffect(() => { if (dialog && (dialog.snapshot.project_id !== evidence.snapshot?.project_id || dialog.snapshot.case_version !== evidence.snapshot?.case_version)) close(); }, [evidence.snapshot]);
  const result = evidence.projection?.stages.find(s => s.stage === "PRICE_EVIDENCE")?.result;
  const view = evidence.workspace;
  const required = dialog?.operation === "withdraw-confirmation" || Boolean(dialog?.snapshot.prior_confirmation_id);
  const open = (operation: "confirm" | "withdraw-confirmation", button: HTMLButtonElement) => {
    if (!evidence.snapshot) return; trigger.current = button; setDialog({ operation, snapshot: evidence.snapshot });
  };
  return <FluentProvider theme={webLightTheme} className="asset-review-region">
    <section aria-label="Nguồn giá và chứng cứ toàn hồ sơ" aria-busy={evidence.loading || evidence.busy}>
      <div className="asset-review-heading"><strong>Nguồn giá & Chứng cứ · Toàn hồ sơ</strong>
        {result && <StatusBadge status={result === "COMPLETE" ? "approved" : result === "BLOCKED" ? "blocking" : "review"} label={CASE_RESULT_LABELS[result]} />}
      </div>
      {evidence.loading && <p role="status">{view ? "Đang cập nhật trạng thái nguồn giá…" : "Đang tải trạng thái nguồn giá…"}</p>}
      {view && <p>Cơ sở đủ điều kiện: {view.covered_count ?? "Chưa xác minh"} / {view.sealed_count} tài sản đã chốt.
        {view.confirmation_current ? " Bộ chứng cứ hiện tại đã được xác nhận." : view.confirmation_withdrawn ? " Xác nhận trước đã được rút." : " Bộ chứng cứ hiện tại chưa được xác nhận."}</p>}
      {result === "NOT_AVAILABLE" && <p>Hoàn tất các điều kiện tiếp nhận, rà soát và chuẩn bị danh mục theo trạng thái hồ sơ.</p>}
      {result === "INCOMPLETE" && <p>Đăng ký nguồn, quyết định phù hợp cho từng tài sản, rồi xác nhận bộ chứng cứ toàn hồ sơ khi hệ thống cho phép.</p>}
      {result === "BLOCKED" && <p role="alert">Có điều kiện đang chặn hồ sơ. Xem trạng thái và mâu thuẫn tại tài sản để xử lý theo quyền hiện tại.</p>}
      {result === "STALE" && <p>Bằng chứng hoặc xác nhận cần xem lại. Tải trạng thái hiện tại, kiểm tra nguồn và đánh giá lại từng dòng bị ảnh hưởng.</p>}
      {evidence.projection?.next_action?.kind === "NO_AUTHORIZED_DOWNSTREAM_ACTION" && <p>Chưa có hành động tiếp theo được phép.</p>}
      {evidence.error && <p role="alert">{evidence.error} Dữ liệu đang hiển thị chưa được xác minh lại; thao tác bị khóa.</p>}
      {evidence.notice && <p role="status" aria-live="polite">{evidence.notice}</p>}
      {evidence.busy && <p role="status">Đang xử lý thao tác nguồn giá…</p>}
      <div className="asset-review-actions">
        {evidence.enabled && evidence.snapshot?.can_confirm && <Button appearance="primary" onClick={e => open("confirm", e.currentTarget)}>
          {evidence.snapshot.prior_confirmation_id ? "Xác nhận lại bộ chứng cứ toàn hồ sơ" : "Xác nhận bộ chứng cứ toàn hồ sơ"}</Button>}
        {evidence.enabled && view?.can_withdraw_confirmation && <Button onClick={e => open("withdraw-confirmation", e.currentTarget)}>Rút xác nhận bộ chứng cứ toàn hồ sơ</Button>}
        <Button disabled={evidence.busy || evidence.loading} appearance={evidence.pending ? "primary" : "secondary"}
          onClick={() => void (evidence.pending ? evidence.recover() : evidence.refresh())}>
          {evidence.pending ? "Kiểm tra kết quả thao tác" : "Tải lại trạng thái nguồn giá"}</Button>
      </div>
      <Dialog open={Boolean(dialog)} onOpenChange={(_, data) => { if (!data.open) close(); }}>
        <DialogSurface><DialogBody><DialogTitle>{dialog?.operation === "confirm" ? "Xác nhận bộ chứng cứ toàn hồ sơ" : "Rút xác nhận bộ chứng cứ toàn hồ sơ"}</DialogTitle>
          <DialogContent>
            <p>Phạm vi: đúng toàn bộ {dialog?.snapshot.lines.length} tài sản trong danh mục hiện tại đã chốt, gồm cả dòng ngoài trang đang xem.</p>
            <p>{dialog?.operation === "confirm" ? "Bạn xác nhận bộ nguồn giá và các quan hệ chứng cứ hiện đang đủ điều kiện cho danh mục này."
              : "Bạn rút xác nhận hiện tại. Nguồn, quyết định, giá làm việc, danh mục và lịch sử được giữ nguyên."}</p>
            <p>Đây không phải lựa chọn nhà cung cấp, xác nhận báo giá, phê duyệt kết quả thẩm định cuối cùng hoặc chốt giá làm việc.</p>
            {required && <EvidenceField label="Lý do xác nhận lại / rút xác nhận" value={reason} onChange={setReason} multiline />}
          </DialogContent>
          <DialogActions><Button onClick={close}>Hủy</Button><Button appearance="primary" disabled={!evidence.enabled || Boolean(required && !reason.trim()) || [...reason.trim()].length > 2000}
            onClick={() => { if (!dialog) return; const approved = dialog; const note = reason.trim(); close();
              void evidence.submit(approved.operation === "confirm"
                ? { operation: "confirm", supersedes_confirmation_id: approved.snapshot.prior_confirmation_id, reason_note: required ? note : null }
                : { operation: "withdraw-confirmation", expected_confirmation_id: approved.snapshot.prior_confirmation_id!, reason_note: note }, approved.snapshot);
            }}>{dialog?.operation === "confirm" ? "Xác nhận toàn bộ chứng cứ" : "Xác nhận rút bộ chứng cứ"}</Button></DialogActions>
        </DialogBody></DialogSurface>
      </Dialog>
    </section>
  </FluentProvider>;
}
