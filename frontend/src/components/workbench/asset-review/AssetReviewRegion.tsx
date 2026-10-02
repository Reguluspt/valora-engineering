import { useEffect, useRef, useState } from "react";
import type { ReviewDecision } from "../../../api/assetReview";
import type { useAssetReview } from "./useAssetReview";

const LABELS = { validate: "Kiểm tra dữ liệu", accepted: "Chấp nhận", flagged: "Gắn cờ", rejected: "Từ chối" };
const FINDINGS: Record<string, string> = {
  asset_name_invalid: "Tên tài sản cần có nội dung và không quá 255 ký tự.",
  quantity_invalid: "Số lượng phải là số dương trong giới hạn cho phép.",
  description_invalid: "Mô tả không đúng định dạng hoặc vượt giới hạn.",
  description_blank: "Mô tả chỉ có khoảng trắng. Hãy sửa mô tả trước khi kiểm tra lại.",
  amount_invalid: "Giá trị tiền không đúng định dạng hoặc vượt giới hạn.",
  reference_invalid: "Thông tin tham chiếu không còn khả dụng.",
};
export function AssetReviewRegion({ review }: { review: ReturnType<typeof useAssetReview> }) {
  const [confirmation, setConfirmation] = useState<{ decision: "validate" | ReviewDecision;
    caseVersion: string; lineId: string } | null>(null);
  const [reason, setReason] = useState("");
  const dialogRef = useRef<HTMLDialogElement>(null);
  const trigger = useRef<HTMLButtonElement | null>(null);
  const close = () => { setConfirmation(null); setReason(""); trigger.current?.focus(); };
  useEffect(() => {
    if (confirmation && dialogRef.current && !dialogRef.current.open) dialogRef.current.showModal();
  }, [confirmation]);
  useEffect(() => {
    if (confirmation && (confirmation.caseVersion !== review.projection?.case_version ||
        confirmation.lineId !== review.context?.line_id || review.loading)) close();
  }, [review.projection?.case_version, review.context?.line_id, review.loading]);
  const outcome = review.projection?.stages.find(stage => stage.stage === "ASSET_REVIEW")?.result;
  const reasonCode = review.context?.reason_code;
  const held = review.negative;
  const currentFindings = review.context?.finding_codes || [];
  const result = review.result;
  const required = confirmation && confirmation.decision !== "validate" &&
    (confirmation.decision !== "accepted" || Boolean(review.context?.prior_decision_id));
  const reasonLength = [...reason.trim()].length;
  const open = (decision: "validate" | ReviewDecision, button: HTMLButtonElement) => {
    if (!review.projection || !review.context?.line_id) return;
    trigger.current = button; setReason("");
    setConfirmation({ decision, caseVersion: review.projection.case_version, lineId: review.context.line_id });
  };
  return <section className="asset-review-region" aria-label="Rà soát tài sản" aria-busy={review.busy || review.loading}>
    <div className="asset-review-heading"><strong>Rà soát tài sản</strong>
      {review.loading ? <span role="status">Đang tải trạng thái…</span>
        : outcome === "COMPLETE" ? <span className="valora-status valora-status--success">Hoàn tất rà soát tài sản</span>
        : <span>{review.row ? `Dòng ${review.row.line_no} · ${review.row.raw_name}` : "Chưa có dòng xử lý khả dụng"}</span>}
    </div>
    {outcome === "COMPLETE" && <p>Toàn bộ danh mục đã được hệ thống xác nhận hoàn tất. Chưa có hành động giai đoạn tiếp theo được phép.</p>}
    {reasonCode === "permission_required" && <p role="alert">Bạn chưa có quyền rà soát tài sản.</p>}
    {reasonCode === "session_required" && <p>Cần phiên bàn làm việc còn hiệu lực. Vui lòng mở lại phiên và tải lại trạng thái.</p>}
    {reasonCode === "line_validation_warning" && <p className="valora-message valora-message--warning">Cảnh báo chưa đủ điều kiện chấp nhận. Hãy sửa dữ liệu chính thức và tải lại trạng thái trước khi kiểm tra lại.</p>}
    {reasonCode === "validation_invalid" && <p className="valora-message valora-message--error">Dữ liệu không hợp lệ. Cần sửa và xác nhận kiểm tra lại; chưa thể chấp nhận.</p>}
    {held && <p className="valora-message valora-message--warning">{reasonCode === "review_flagged" ? "Dòng đã gắn cờ." : "Dòng đã từ chối."} Việc sửa hoặc kiểm tra lại không xóa quyết định này. Xác nhận kiểm tra hợp lệ, rồi chủ động đổi quyết định và ghi lý do.</p>}
    {review.action?.kind === "BLOCKER" && !held && reasonCode !== "validation_invalid" &&
      <p>Có vấn đề bắt buộc cần xử lý trước. Rà soát không tự xóa vấn đề hoặc sửa nguồn dữ liệu.</p>}
    {currentFindings.length > 0 && <ul aria-label="Điểm cần chỉnh sửa">{currentFindings.map((code, i) =>
      <li key={`${code}-${i}`}>{FINDINGS[code] || "Thông tin cần được kiểm tra lại."} <small>({code})</small></li>)}</ul>}
    {review.notice && <p role="status" aria-live="polite">{review.notice}</p>}
    {result && <p role="status">Kết quả thao tác{result.historical ? " trước đây" : " đã ghi nhận"}: {
      result.result.validation_outcome === "valid" ? "Hợp lệ" : result.result.validation_outcome === "warning"
        ? "Cảnh báo — cần sửa trước khi chấp nhận" : result.result.validation_outcome === "invalid"
        ? "Không hợp lệ — cần chỉnh sửa" : LABELS[result.result.target_review_status || "validate"]}.
      Kết quả này không thay thế trạng thái danh mục hiện tại.</p>}
    <div className="asset-review-actions">
      {review.canValidate && <button className={`valora-button valora-button--${review.canAccept ? "secondary" : "primary"}`} onClick={e => open("validate", e.currentTarget)}>Kiểm tra dữ liệu</button>}
      {review.canReview && (["accepted", "flagged", "rejected"] as ReviewDecision[])
        .filter(decision => (decision !== "accepted" || review.canAccept) &&
          !(held && reasonCode === `review_${decision}`))
        .map(decision => <button key={decision} className={`valora-button valora-button--${decision === "accepted" ? "primary" : "secondary"}`}
          onClick={e => open(decision, e.currentTarget)}>{LABELS[decision]}</button>)}
      {review.pending ? <button className="valora-button valora-button--primary" disabled={review.busy}
        onClick={() => void review.recover()}>Kiểm tra kết quả thao tác</button>
        : <button className="valora-button valora-button--secondary" disabled={review.loading || review.busy}
          onClick={() => void review.refresh()}>Tải lại trạng thái rà soát</button>}
      {review.busy && <span role="status">Đang ghi nhận / kiểm tra kết quả…</span>}
    </div>
    {confirmation && <dialog ref={dialogRef} className="asset-review-dialog" aria-labelledby="asset-review-confirm-title"
      onCancel={event => { event.preventDefault(); close(); }}>
      <h2 id="asset-review-confirm-title">Xác nhận {LABELS[confirmation.decision].toLowerCase()}</h2>
      <p>Dòng {review.row?.line_no}: {review.row?.raw_name}</p>
      <p>{confirmation.decision === "validate" ? "Hệ thống kiểm tra dữ liệu chính thức và ghi một kết quả kiểm tra mới. Kết quả không tự chấp nhận tài sản."
        : "Quyết định này được ghi nhận vào dữ liệu chính thức và lịch sử rà soát."}</p>
      {confirmation.decision !== "validate" && <label>Lý do {required ? "(bắt buộc)" : "(không bắt buộc)"}
        <textarea autoFocus value={reason} onChange={e => setReason(e.target.value)} aria-label="Lý do quyết định" />
        <small>{reasonLength}/2000 ký tự</small>
      </label>}
      <div className="asset-review-actions">
        <button className="valora-button valora-button--secondary" onClick={close}>Hủy</button>
        <button className="valora-button valora-button--primary" disabled={review.busy ||
          Boolean(required && !reason.trim()) || reasonLength > 2000} onClick={() => {
            const approved = confirmation;
            const note = reason;
            close();
            void review.submit(approved.decision, note, approved.caseVersion, approved.lineId);
          }}>Xác nhận {LABELS[confirmation.decision].toLowerCase()}</button>
      </div>
    </dialog>}
  </section>;
}
