import { useEffect, useRef, useState } from "react";
import { Button, Dialog, DialogSurface, DialogBody, DialogTitle, DialogContent, DialogActions, FluentProvider, webLightTheme } from "@fluentui/react-components";
import { fetchEvidenceSource, type EvidencePreparation, type EvidenceSourceView, type EvidenceSourceRead, type EvidenceIntent } from "../../../api/priceEvidence";
import { SourceForm } from "./SourceForm";
import { RelevanceForm } from "./RelevanceForm";
import { EvidenceField, categoryLabels } from "./EvidenceFields";
import { evidenceError, type PriceEvidenceController } from "./usePriceEvidence";

type DialogState = { kind: "register" | "correct" | "decide" | "withdraw" | "source"; snapshot: EvidencePreparation;
  source?: EvidenceSourceView; target?: "source" | "relationship" | "decision" };
export function EvidenceWorkspacePanel({ evidence, lineId, lineLabel, projectId }: {
  evidence: PriceEvidenceController; lineId: string; lineLabel: string; projectId: string;
}) {
  const [dialog, setDialog] = useState<DialogState | null>(null), [material, setMaterial] = useState<EvidenceSourceRead | null>(null);
  const [reading, setReading] = useState(false), [readError, setReadError] = useState("");
  const [reason, setReason] = useState("");
  const trigger = useRef<HTMLButtonElement | null>(null), readGeneration = useRef(0);
  const close = () => { ++readGeneration.current; setDialog(null); setMaterial(null); setReadError(""); setReason(""); trigger.current?.focus(); };
  useEffect(() => { if (dialog && (!evidence.snapshot || dialog.snapshot.project_id !== evidence.snapshot.project_id ||
    dialog.kind !== "source" && dialog.snapshot.case_version !== evidence.snapshot.case_version)) close(); }, [evidence.snapshot]);
  useEffect(() => () => { ++readGeneration.current; }, []);
  const readSource = async (revision: string) => {
    const gen = ++readGeneration.current; setReading(true); setReadError(""); setMaterial(null);
    try { const value = await fetchEvidenceSource(projectId, revision);
      if (value.project_id !== projectId || value.evidence_revision_id !== revision) throw new Error("Scope mismatch");
      if (gen === readGeneration.current) setMaterial(value);
    } catch (caught) { if (gen === readGeneration.current) setReadError(evidenceError((caught as { status?: number }).status || 0)); }
    finally { if (gen === readGeneration.current) setReading(false); }
  };
  const open = (kind: DialogState["kind"], button: HTMLButtonElement, source?: EvidenceSourceView, target?: DialogState["target"]) => {
    if (!evidence.snapshot) return;
    trigger.current = button; setDialog({ kind, source, target, snapshot: evidence.snapshot }); setReason("");
    if (source && (kind === "source" || kind === "correct")) void readSource(source.evidence_revision_id);
  };
  const submit = (intent: EvidenceIntent) => {
    if (!dialog || !evidence.enabled) return;
    const approved = dialog.snapshot; close(); void evidence.submit(intent, approved);
  };
  const view = evidence.workspace?.line_id === lineId ? evidence.workspace : null;
  const title = dialog?.kind === "register" ? "Đăng ký nguồn giá" : dialog?.kind === "correct" ? "Tạo phiên bản nguồn thay thế"
    : dialog?.kind === "decide" ? "Đánh giá nguồn cho tài sản" : dialog?.kind === "withdraw" ? "Rút chứng cứ đã chọn" : "Nội dung nguồn đã lưu giữ";
  return <FluentProvider theme={webLightTheme}>
    <section aria-label="Chứng cứ của tài sản" aria-busy={evidence.loading}>
      <h3>{lineLabel}</h3>
      {evidence.error && <p role="alert">{evidence.error}</p>}
      {evidence.loading && <p role="status">{view ? "Đang cập nhật chứng cứ…" : "Đang tải chứng cứ của tài sản…"}</p>}
      {view && <p>{view.line_covered === null ? "Chưa xác minh được cơ sở của dòng." : view.line_covered ? "Dòng có cơ sở đủ điều kiện theo hệ thống." : "Dòng chưa có cơ sở đủ điều kiện."}
        {view.line_hold && " Còn mâu thuẫn cần xử lý bằng quyết định rõ ràng."}</p>}
      {evidence.enabled && evidence.snapshot?.can_register && <Button appearance="primary" onClick={e => open("register", e.currentTarget)}>Đăng ký nguồn giá</Button>}
      {view && !evidence.error && !view.sources.length && <p>Chưa có nguồn đã đăng ký. Đăng ký nguồn rồi đánh giá riêng cho từng tài sản; đăng ký không tự hoàn tất chứng cứ.</p>}
      {view?.sources.map(source => <section key={source.evidence_revision_id} className="asset-context-card" aria-label={`${source.origin} · Phiên bản ${source.revision}`}>
        <h4>{source.origin} · Phiên bản {source.revision}</h4>
        <dl className="asset-context-facts">
          <div><dt>Loại nguồn</dt><dd>{categoryLabels[source.category]}</dd></div>
          <div><dt>Trạng thái nguồn</dt><dd>{source.withdrawn ? "Đã rút" : source.current ? "Phiên bản hiện tại" : "Đã được thay thế"}{source.expired ? " · Đã hết hạn" : ""}</dd></div>
          <div><dt>Ngày nguồn</dt><dd>{source.date_unknown ? "Không xác định; đã ghi lý do" : source.effective_date}</dd></div>
          <div><dt>Ghi nhận</dt><dd>{new Date(source.captured_at).toLocaleString("vi-VN")}</dd></div>
          <div><dt>Hết hạn nguồn</dt><dd>{source.expires_at ? new Date(source.expires_at).toLocaleString("vi-VN") : "Không ghi hạn nguồn"}</dd></div>
          <div><dt>Quyết định cho dòng này</dt><dd>{!source.decision ? "Chưa đánh giá" : source.decision.disposition === "qualifying_basis" ? "Chấp nhận làm cơ sở"
            : source.decision.disposition === "unresolved_concern" ? "Còn mâu thuẫn cần xử lý" : "Loại khỏi cơ sở"}
            {source.decision?.withdrawn ? " · Đã rút" : ""}</dd></div>
          {source.decision && <><div><dt>Hiện đủ điều kiện</dt><dd>{source.decision.qualifying ? "Có" : "Không"}</dd></div>
            <div><dt>Hạn rà soát</dt><dd>{new Date(source.decision.review_due_at).toLocaleString("vi-VN")}{source.decision.review_expired ? " · Đã hết hạn" : ""}</dd></div></>}
        </dl>
        <details><summary>Định danh nguồn và quan hệ</summary><p>Nguồn: {source.source_id}</p><p>Phiên bản: {source.evidence_revision_id}</p>
          {source.decision && <><p>Dòng: {source.decision.line_id}</p><p>Quan hệ: {source.decision.relationship_id}</p><p>Quyết định: {source.decision.decision_id}</p>
            <p>Phiên bản được đánh giá: {source.decision.evidence_revision_id}</p></>}</details>
        <div className="asset-review-actions">
          <Button onClick={e => open("source", e.currentTarget, source)}>Xem nội dung nguồn</Button>
          {evidence.enabled && (source.can_accept || source.can_reject) && <Button onClick={e => open("decide", e.currentTarget, source)}>Đánh giá cho tài sản này</Button>}
          {evidence.enabled && source.can_correct && <Button onClick={e => open("correct", e.currentTarget, source)}>Tạo phiên bản thay thế</Button>}
          {evidence.enabled && source.can_withdraw && <Button onClick={e => open("withdraw", e.currentTarget, source, "source")}>Rút nguồn</Button>}
          {evidence.enabled && source.decision?.can_withdraw && <>
            <Button onClick={e => open("withdraw", e.currentTarget, source, "relationship")}>Rút quan hệ</Button>
            <Button onClick={e => open("withdraw", e.currentTarget, source, "decision")}>Rút quyết định</Button>
          </>}
        </div>
      </section>)}
      {view?.next_offset !== null && view && <Button disabled={evidence.loading} onClick={() => void evidence.loadMore()}>Tải thêm nguồn</Button>}
      <Dialog open={Boolean(dialog)} onOpenChange={(_, data) => { if (!data.open) close(); }}>
        <DialogSurface><DialogBody><DialogTitle>{title}</DialogTitle><DialogContent>
          {reading && <p role="status">Đang đọc nguồn qua truy cập có ghi nhận lịch sử…</p>}
          {readError && <p role="alert">{readError} <Button onClick={() => { if (dialog?.source) void readSource(dialog.source.evidence_revision_id); }}>Đọc lại nguồn</Button></p>}
          {(dialog?.kind === "register" || dialog?.kind === "correct" && material) &&
            <SourceForm projectId={projectId} initial={dialog.kind === "correct" ? material!.material : undefined}
              sources={(view?.sources || []).filter(s => s.source_id !== dialog.source?.source_id)} moreSources={view?.next_offset != null}
              onMore={() => void evidence.loadMore()} onCancel={close}
              onSave={(sourceMaterial, note) => submit({ operation: "register", source_id: dialog.source?.source_id || crypto.randomUUID(),
                predecessor_revision_id: dialog.source?.evidence_revision_id || null, material: sourceMaterial, reason_note: note || null })} />}
          {dialog?.kind === "decide" && dialog.source && <RelevanceForm source={dialog.source} lineLabel={lineLabel} onCancel={close}
            onSave={(facts, note) => submit({ operation: "decide", line_id: lineId, evidence_revision_id: dialog.source!.evidence_revision_id,
              predecessor_relationship_id: dialog.source!.decision?.relationship_id || null, prior_decision_id: dialog.source!.decision?.decision_id || null,
              expected_line_proof_sha256: dialog.snapshot.lines.find(l => l.line_id === lineId)!.proof_sha256, facts, reason_note: note || null })} />}
          {dialog?.kind === "withdraw" && <><p>Rút đúng {dialog.target === "source" ? "nguồn của toàn hồ sơ" : dialog.target === "relationship" ? "quan hệ với tài sản đang chọn" : "quyết định cho tài sản đang chọn"}: {dialog.source?.origin} · Phiên bản {dialog.source?.revision}.</p>
            <p>Lịch sử không bị xóa. Việc rút nguồn có thể ảnh hưởng đến mọi dòng đang dùng nguồn đó; mâu thuẫn vẫn cần quyết định xử lý riêng.</p>
            <EvidenceField label="Lý do rút chứng cứ" multiline value={reason} onChange={setReason} /></>}
          {dialog?.kind === "source" && material && <>
            <p>{categoryLabels[material.material.category]} · {material.material.origin} · Phiên bản {material.revision}</p>
            <p>{material.material.reference}</p><p>Vị trí: {material.material.locator}</p>
            <p>{material.material.retained_text}</p><p>Hạn chế: {material.material.limitations}</p>
            {material.material.value && <dl className="asset-context-facts">{Object.entries(material.material.value).map(([key, value]) =>
              <div key={key}><dt>{({ amount: "Giá trị", range_upper: "Giới hạn trên", currency: "Tiền tệ", unit_basis: "Đơn vị", quantity_basis: "Số lượng", tax: "Thuế", delivery: "Giao hàng", condition: "Tình trạng", locator: "Vị trí" } as Record<string, string>)[key]}</dt><dd>{value ?? "Không ghi nhận"}</dd></div>)}</dl>}
            {material.material.explanation && <><p>Giả định: {material.material.explanation.assumptions}</p><p>Phép tính: {material.material.explanation.calculations}</p></>}
            {material.material.historical && <><p>Ngày thẩm định: {material.material.historical.appraisal_date}</p><p>{material.material.historical.result_excerpt}</p><p>{material.material.historical.result_locator}</p></>}
            {material.predecessor_revision_id && <Button onClick={() => void readSource(material.predecessor_revision_id!)}>Xem phiên bản nguồn trước</Button>}
          </>}
        </DialogContent>
          {(dialog?.kind === "source" || dialog?.kind === "withdraw" || reading || readError) && <DialogActions><Button onClick={close}>Đóng</Button>
            {dialog?.kind === "withdraw" && <Button appearance="primary" disabled={!evidence.enabled || !reason.trim() || [...reason.trim()].length > 2000}
              onClick={() => submit({ operation: "withdraw", target_kind: dialog.target!, reason_note: reason.trim(),
                target_id: dialog.target === "source" ? dialog.source!.evidence_revision_id : dialog.target === "relationship" ? dialog.source!.decision!.relationship_id : dialog.source!.decision!.decision_id })}>Xác nhận rút chứng cứ</Button>}
          </DialogActions>}
        </DialogBody></DialogSurface>
      </Dialog>
    </section>
  </FluentProvider>;
}
