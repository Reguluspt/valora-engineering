import { useEffect, useRef, useState } from "react";
import { Button, Dialog, DialogSurface, DialogBody, DialogTitle, DialogContent, DialogActions, Field, Textarea } from "@fluentui/react-components";
import { saveAssetLineDraft, commitAssetLineDraft } from "../../../api/projects";
import { fetchProjectDraftState } from "../../../api/projects";
import type { AssetLineGridRow } from "../AssetGridTypes";
import { t } from "../../../i18n";

export function DescriptionPreparation({ projectId, sessionId, row, enabled, onCommitted }: {
  projectId: string; sessionId?: string; row: AssetLineGridRow; enabled: boolean; onCommitted: () => void;
}) {
  const official = row.description ?? "";
  const [value, setValue] = useState(official);
  const [saved, setSaved] = useState<{ value: string; version: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [existingDraft, setExistingDraft] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [confirming, setConfirming] = useState(false);
  const alive = useRef(true);
  const locked = useRef(false);
  const trigger = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    alive.current = true;
    if (!sessionId) { setLoading(false); return; }
    void fetchProjectDraftState(projectId).then(response => {
      if (!alive.current) return;
      setExistingDraft(response.items.some(item => item.asset_line_id === row.project_asset_line_id && item.changed_fields.includes("description")));
    }).catch(() => { if (alive.current) setNotice("Chưa tải được nháp mô tả. Tải lại bàn làm việc trước khi lưu hoặc áp dụng."); })
      .finally(() => { if (alive.current) setLoading(false); });
    return () => { alive.current = false; };
  }, [projectId, sessionId, row.project_asset_line_id]);
  const count = [...value].length;
  const canSave = enabled && !loading && !busy && count <= 5000 && Number.isSafeInteger(row.row_version) && row.row_version! > 0;
  const canCommit = canSave && saved?.value === value && saved.version === row.row_version;
  const save = async () => {
    if (!canSave || locked.current) return;
    locked.current = true; setBusy(true); setNotice("");
    try {
      await saveAssetLineDraft(projectId, row.project_asset_line_id, { field_key: "description", draft_value: value,
        base_value: row.description ?? null, version_token: String(row.row_version) });
      if (alive.current) { setSaved({ value, version: row.row_version! }); setNotice("Đã lưu nháp. Mô tả chính thức chưa thay đổi."); }
    } catch (error) {
      if (alive.current) setNotice((error as { status?: number }).status === 409
        ? "Dòng đã thay đổi. Tải lại bàn làm việc rồi xem lại nháp; chưa áp dụng dữ liệu."
        : "Chưa lưu được nháp. Kiểm tra phiên làm việc và tải lại dữ liệu.");
    } finally { locked.current = false; if (alive.current) setBusy(false); }
  };
  const commit = async () => {
    if (!canCommit || locked.current) return;
    locked.current = true; setBusy(true); setConfirming(false);
    try {
      await commitAssetLineDraft(projectId, row.project_asset_line_id,
        { field_keys: ["description"], confirm: true, version_token: String(saved!.version) });
      if (alive.current) { setSaved(null); setNotice("Đã ghi nhận mô tả chính thức. Cần kiểm tra dữ liệu và rà soát lại trước khi xác nhận danh mục."); onCommitted(); }
    } catch (error) {
      if (alive.current) {
        setNotice((error as { status?: number }).status === 409 ? "Dòng hoặc nháp đã thay đổi. Tải lại và xem lại trước khi áp dụng."
          : "Chưa xác định được mô tả đã áp dụng. Tải lại dữ liệu chính thức và nháp trước khi xác nhận mới.");
        setSaved(null); onCommitted();
      }
    } finally { locked.current = false; if (alive.current) setBusy(false); }
  };
  return <section className="asset-description" aria-label="Mô tả tài sản" aria-busy={busy || loading}>
    <strong>Mô tả · Dòng {row.line_no}: {row.raw_name}</strong>
    <p>Mô tả chính thức: {official.trim() ? official : "Chưa có mô tả. Chọn dòng tài sản và chuẩn bị mô tả."}</p>
    <Field label="Mô tả nháp" hint={`${count}/5000 ký tự · ${saved?.value === value ? "Đã lưu nháp" : "Chưa lưu"}`}>
      <Textarea value={value} onChange={(_, data) => setValue(data.value)} disabled={!enabled || busy || loading} resize="vertical" />
    </Field>
    <p>{t("workbench.draftWarning")}</p>
    {existingDraft && !saved && <p>Dòng có nháp mô tả đã lưu. Nội dung trên đây là mô tả chính thức; nhập nội dung cần dùng và lưu nháp để xem lại trước khi áp dụng.</p>}
    {saved && saved.version !== row.row_version && <p role="alert">Nháp dựa trên dữ liệu cũ. Xem lại mô tả chính thức, chỉnh sửa và lưu nháp mới.</p>}
    {notice && <p role="status">{notice}</p>}
    <div className="asset-review-actions">
      <Button disabled={!canSave} onClick={() => void save()}>{t("action.saveDraft")}</Button>
      <Button ref={trigger} disabled={!canCommit} onClick={() => setConfirming(true)} appearance="primary">Áp dụng nháp mô tả</Button>
    </div>
    <Dialog open={confirming && enabled} onOpenChange={(_, data) => { setConfirming(data.open); if (!data.open) trigger.current?.focus(); }}>
      <DialogSurface><DialogBody>
        <DialogTitle>Xác nhận áp dụng nháp mô tả</DialogTitle>
        <DialogContent><p>Mô tả đã lưu sẽ cập nhật dữ liệu chính thức của dòng {row.line_no}: {row.raw_name}.</p><p>{saved?.value}</p></DialogContent>
        <DialogActions><Button onClick={() => { setConfirming(false); trigger.current?.focus(); }}>Hủy</Button>
          <Button appearance="primary" disabled={!canCommit} onClick={() => void commit()}>Xác nhận áp dụng mô tả</Button></DialogActions>
      </DialogBody></DialogSurface>
    </Dialog>
  </section>;
}
