import { useEffect, useRef, useState } from "react";
import { Button, Dialog, DialogSurface, DialogBody, DialogTitle, DialogContent, DialogActions, Field, Textarea,
  FluentProvider, webLightTheme } from "@fluentui/react-components";
import { StatusBadge } from "../../common/StatusBadge";
import { CASE_RESULT_LABELS } from "../../case-overview/caseOverviewPresentation";
import type { useAssetWorkbench } from "./useAssetWorkbench";
import type { WorkbenchPreparation } from "../../../api/assetWorkbench";
import { DescriptionPreparation } from "./DescriptionPreparation";
import type { AssetLineGridRow } from "../AssetGridTypes";
import { t } from "../../../i18n";

export function AssetWorkbenchRegion({ workbench, row, projectId, sessionId, onCommitted }: {
  workbench: ReturnType<typeof useAssetWorkbench>; row: AssetLineGridRow | null; projectId: string;
  sessionId?: string; onCommitted: () => void;
}) {
  const [confirmation, setConfirmation] = useState<{ operation: "confirm" | "withdraw"; snapshot: WorkbenchPreparation } | null>(null);
  const [reason, setReason] = useState("");
  const trigger = useRef<HTMLButtonElement | null>(null);
  const close = () => { setConfirmation(null); setReason(""); trigger.current?.focus(); };
  useEffect(() => {
    if (confirmation && (confirmation.snapshot !== workbench.snapshot || workbench.loading ||
      (confirmation.operation === "confirm" ? !workbench.canConfirm : !workbench.canWithdraw))) close();
  }, [workbench.snapshot, workbench.loading, workbench.canConfirm, workbench.canWithdraw]);
  const outcome = workbench.projection?.stages.find(stage => stage.stage === "ASSET_WORKBENCH")?.result;
  const required = confirmation?.operation === "withdraw" || Boolean(confirmation?.snapshot.prior_confirmation_id);
  const open = (operation: "confirm" | "withdraw", button: HTMLButtonElement) => {
    if (!workbench.snapshot) return;
    trigger.current = button; setReason(""); setConfirmation({ operation, snapshot: workbench.snapshot });
  };
  return <FluentProvider theme={webLightTheme} className="asset-review-region">
    <section aria-label={t("workbench.preparation")} aria-busy={workbench.loading || workbench.busy}>
      <div className="asset-review-heading"><strong>{t("workbench.preparation")}</strong>
        {workbench.loading ? <span role="status">Đang tải trạng thái…</span> : outcome &&
          <StatusBadge status={outcome === "COMPLETE" ? "approved" : outcome === "BLOCKED" ? "blocking" : "review"} label={CASE_RESULT_LABELS[outcome]} />}
      </div>
      <p>{t("workbench.priceOptional")}</p>
      {outcome === "COMPLETE" && <p>{t("workbench.downstreamHold")}</p>}
      {outcome === "NOT_AVAILABLE" && <p>Hoàn tất điều kiện tiếp nhận và rà soát theo trạng thái hồ sơ trước khi chuẩn bị danh mục.</p>}
      {outcome === "BLOCKED" && <p role="alert">Hồ sơ đang bị chặn. Xử lý điều kiện được hệ thống chỉ ra; chưa thể xác nhận danh mục.</p>}
      {outcome === "STALE" && <p>Thông tin hoặc bằng chứng rà soát đã thay đổi. Kiểm tra, rà soát lại dữ liệu chính thức rồi xác nhận lại với lý do khi hệ thống cho phép.</p>}
      {outcome === "INCOMPLETE" && <p>Mỗi tài sản cần có mô tả chính thức. Sau khi kiểm tra và rà soát hoàn tất, xác nhận toàn bộ danh mục.</p>}
      {!workbench.loading && !workbench.snapshot && <p>Chưa có điều kiện thao tác khả dụng. Kiểm tra quyền và phiên bàn làm việc, rồi tải lại trạng thái.</p>}
      {workbench.notice && <p role="status" aria-live="polite">{workbench.notice}</p>}
      {workbench.receipt && <p>Kết quả thao tác {workbench.receipt.historical ? "trước đây" : "đã ghi nhận"}; trạng thái hiện tại chỉ được xác định từ hồ sơ đã tải lại.</p>}
      <div className="asset-review-actions">
        {workbench.canConfirm && <Button appearance="primary" onClick={e => open("confirm", e.currentTarget)}>
          {t(workbench.snapshot?.prior_confirmation_id ? "workbench.reconfirmSet" : "workbench.confirmSet")}</Button>}
        {workbench.canWithdraw && <Button onClick={e => open("withdraw", e.currentTarget)}>{t("workbench.withdrawSet")}</Button>}
        <Button disabled={workbench.loading || workbench.busy} onClick={() => void (workbench.pending ? workbench.recover() : workbench.refresh())}>
          {workbench.pending ? "Kiểm tra kết quả xác nhận" : "Tải lại trạng thái danh mục"}</Button>
      </div>
      {row ? <DescriptionPreparation key={`${sessionId}:${row.project_asset_line_id}:${row.row_version}`} projectId={projectId}
        sessionId={sessionId} row={row} enabled={workbench.canEdit} onCommitted={onCommitted} />
        : <p>Chọn một dòng trong bảng để xem và chuẩn bị mô tả.</p>}
      <Dialog open={Boolean(confirmation)} onOpenChange={(_, data) => { if (!data.open) close(); }}>
        <DialogSurface><DialogBody>
          <DialogTitle>{confirmation?.operation === "withdraw" ? "Xác nhận rút xác nhận danh mục" : t("workbench.confirmSet")}</DialogTitle>
          <DialogContent>
            <p>{confirmation?.operation === "withdraw" ? "Rút tuyên bố sẵn sàng của danh mục hiện tại. Lịch sử xác nhận được giữ nguyên; mô tả, giá và quyết định rà soát không bị xóa." : t("workbench.confirmMeaning")}</p>
            <p>Phạm vi: toàn bộ {confirmation?.snapshot.line_versions.length} tài sản đã chốt, gồm cả dòng ngoài trang và bộ lọc đang xem.</p>
            <p>{t("workbench.draftWarning")}</p>
            {required && <Field label="Lý do (bắt buộc)" hint={`${[...reason.trim()].length}/2000 ký tự`}>
              <Textarea value={reason} onChange={(_, data) => setReason(data.value)} /></Field>}
          </DialogContent>
          <DialogActions><Button onClick={close}>Hủy</Button>
            <Button appearance="primary" disabled={Boolean(required && !reason.trim()) || [...reason.trim()].length > 2000 || workbench.busy}
              onClick={() => { if (!confirmation) return; const approved = confirmation; const note = reason; close();
                void workbench.submit(approved.operation, note, approved.snapshot); }}>
              {confirmation?.operation === "withdraw" ? "Xác nhận rút" : "Xác nhận danh mục"}</Button></DialogActions>
        </DialogBody></DialogSurface>
      </Dialog>
    </section>
  </FluentProvider>;
}
