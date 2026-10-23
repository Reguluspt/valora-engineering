import React, { FormEvent, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { Button, Field, Input, Textarea, Checkbox, FluentProvider, webLightTheme, makeStyles } from "@fluentui/react-components";
import { APP_ROUTES, projectPreliminaryIntakePath } from "../../contracts/valoraV23";
import { CreateScope, createIntents } from "./preliminaryCreateIntent";
import { PreliminaryCreateRecovery } from "./PreliminaryCreateRecovery";
import "./precase.css";

const useStyles = makeStyles({
  page: { display: "flex", flexDirection: "column", gap: "var(--valora-space-lg)", minHeight: 0,
    backgroundColor: "var(--valora-color-canvas)", "& > *": { flexShrink: 0 } },
  field: { "& label": { display: "block" } },
  distinct: { maxWidth: "52rem" },
});

export function PreliminaryRequestCreatePage({ scope, canCreate, onNavigate, onSessionExpired }: {
  scope: CreateScope; canCreate: boolean; onNavigate: (path: string) => void; onSessionExpired: () => void;
}) {
  const styles = useStyles();
  const store = createIntents(scope);
  useSyncExternalStore(store.subscribe, store.snapshot);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [feedback, setFeedback] = useState("");
  const [distinct, setDistinct] = useState(false);
  const locked = useRef(false);
  const mounted = useRef(true);
  const errorRef = useRef<HTMLParagraphElement>(null);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => { if (feedback) errorRef.current?.focus(); }, [feedback]);
  const uncertain = store.markers.some(m => m.phase === "UNCERTAIN");
  const retained = store.markers.length > 0;
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (locked.current || !canCreate || uncertain || store.problem || (retained && !distinct)) return;
    locked.current = true; setFeedback(""); setDistinct(false);
    try {
      const result = await store.submit(name, description, distinct);
      if (result && mounted.current && store.isActive()) onNavigate(projectPreliminaryIntakePath(result.project.id));
    } catch (error) { if (mounted.current) setFeedback(error instanceof Error ? error.message : "Chưa thể tạo yêu cầu."); }
    finally { locked.current = false; }
  };
  return <FluentProvider theme={webLightTheme} className={`precase-create-page ${styles.page}`}>
    <header className="precase-create-header"><p>Yêu cầu sơ bộ</p><h1>Tạo yêu cầu sơ bộ</h1>
      <span>Bạn có thể tạo yêu cầu mà chưa gắn khách hàng. Cần gắn khách hàng trước khi chuyển sang thẩm định chính thức.</span>
    </header>
    {(retained || store.problem || store.message) && <PreliminaryCreateRecovery store={store} onNavigate={onNavigate} onSessionExpired={onSessionExpired} />}
    {!canCreate && <p role="alert">Tài khoản chưa có quyền tạo yêu cầu sơ bộ.</p>}
    {retained && !uncertain && <Checkbox className={styles.distinct} checked={distinct} label={store.markers.some(marker => marker.phase === "PARKED")
      ? "Tạo yêu cầu khác: tôi xác nhận đây là ý định mới; yêu cầu tạm gác vẫn chưa rõ kết quả."
      : "Tạo yêu cầu khác: tôi xác nhận đây là ý định mới."} onChange={(_, data) => {
      setDistinct(!!data.checked); if (data.checked) store.retireCommitted();
    }} />}
    <form aria-busy={store.busy.size > 0} className="precase-create-form valora-panel" onSubmit={submit}>
      <div className="valora-panel__header">Thông tin yêu cầu</div>
      <div className="valora-panel__body precase-create-fields">
        <Field className={styles.field} label="Tên yêu cầu sơ bộ" required><Input name="name" value={name} disabled={!canCreate || uncertain || store.busy.size > 0} onChange={(_, data) => setName(data.value)} /></Field>
        <Field className={styles.field} label="Mô tả (không bắt buộc)"><Textarea name="description" value={description} disabled={!canCreate || uncertain || store.busy.size > 0} rows={4} onChange={(_, data) => setDescription(data.value)} /></Field>
        {feedback && <p role="alert" tabIndex={-1} ref={errorRef}>{feedback}</p>}
      </div>
      <div className="valora-panel__footer precase-create-actions">
        <Button onClick={() => onNavigate(APP_ROUTES.preliminaryRequestManagement)} type="button">Hủy</Button>
        <Button appearance="primary" type="submit" disabled={!canCreate || !name || uncertain || !!store.problem || store.busy.size > 0 || (retained && !distinct)}>{store.busy.size ? "Đang tạo…" : "Tạo yêu cầu sơ bộ"}</Button>
      </div>
    </form>
  </FluentProvider>;
}
