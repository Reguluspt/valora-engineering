import React, { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { Button, Checkbox, makeStyles } from "@fluentui/react-components";
import { APP_ROUTES, projectPreliminaryIntakePath } from "../../contracts/valoraV23";
import { PreliminaryCreateIntents } from "./preliminaryCreateIntent";
import { MessageBar } from "../ui/MessageBar";

const useStyles = makeStyles({
  panel: { width: "min(100%, 52rem)", boxSizing: "border-box", minWidth: 0 },
  heading: { margin: 0, fontSize: "inherit", fontWeight: "inherit" },
  body: { display: "grid", gap: "var(--valora-space-lg)", minWidth: 0 },
  intent: { display: "grid", gap: "var(--valora-space-md)", minWidth: 0,
    border: "1px solid var(--valora-color-border-subtle)", borderRadius: "var(--valora-radius-control)",
    padding: "var(--valora-space-lg)", backgroundColor: "var(--valora-color-surface-primary)",
    "& p": { margin: 0, overflowWrap: "anywhere" } },
  header: { display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: "var(--valora-space-sm)" },
  intentHeading: { margin: 0, fontSize: "var(--valora-font-size-body)", fontWeight: "var(--valora-font-weight-semibold)" },
  locator: { display: "block", overflowWrap: "anywhere", fontFamily: "var(--valora-font-family-mono)", fontSize: "var(--valora-font-size-caption)" },
  actions: { display: "flex", flexWrap: "wrap", alignItems: "center", gap: "var(--valora-space-sm)",
    "& > button": { maxWidth: "100%", whiteSpace: "normal", textAlign: "left" },
    "& > a": { display: "inline-flex", alignItems: "center", textDecorationLine: "none" } },
  replay: { display: "grid", gap: "var(--valora-space-sm)", minWidth: 0 },
});

export function PreliminaryCreateRecovery({ store, onNavigate, onSessionExpired }: {
  store: PreliminaryCreateIntents; onNavigate: (path: string) => void; onSessionExpired: () => void;
}) {
  const styles = useStyles();
  useSyncExternalStore(store.subscribe, store.snapshot);
  const [confirmed, setConfirmed] = useState<string | null>(null);
  const feedback = useRef<HTMLDivElement>(null);
  const storageProblem = store.problem && store.markers.some(marker => marker.phase === "COMMITTED")
    ? "Bộ nhớ trình duyệt chưa lưu được cập nhật khôi phục. Trạng thái của từng mã vẫn được giữ trong trang này; hãy tải mã khôi phục và liên hệ quản trị viên."
    : store.problem;
  useEffect(() => { if (store.message) feedback.current?.focus(); }, [store.message]);
  return <section aria-label="Khôi phục yêu cầu sơ bộ" className={`valora-panel ${styles.panel}`}>
    <div className="valora-panel__header"><h2 className={styles.heading}>Khôi phục yêu cầu sơ bộ</h2></div>
    <div className={`valora-panel__body ${styles.body}`}>
      {storageProblem && <MessageBar tone="error" title="Bộ nhớ khôi phục cần được kiểm tra" message={storageProblem} />}
      {store.message && <div tabIndex={-1} ref={feedback}><MessageBar title="Thao tác gần nhất" message={store.message} /></div>}
      {store.markers.map((marker, index) => {
        const original = store.original(marker.request_id);
        const content = original ? JSON.parse(original) as { name: string; description: string | null } : null;
        return <section key={marker.request_id} aria-label={`Yêu cầu ${marker.request_id}`} className={styles.intent}>
          <div className={styles.header}><h3 className={styles.intentHeading}>Yêu cầu {index + 1}</h3>
            <span className={`valora-status valora-status--${marker.phase === "COMMITTED" ? "success" : "warning"}`}>{marker.phase === "COMMITTED" ? "Đã xác nhận" : "Chưa xác định"}</span></div>
          <p>Mã khôi phục: <code className={styles.locator}>{marker.request_id}</code></p>
          {marker.phase === "COMMITTED" ? <>
            <p>Đã xác nhận tạo hồ sơ.{store.conflict.has(marker.request_id) && " Nội dung bị từ chối chưa được lưu."}</p>
          </> : <>
            <p>Chưa xác định yêu cầu đã được tạo hay chưa.</p>
            {marker.phase === "PARKED" && <p>Chưa thể xác định kết quả. Không tạo lại cùng yêu cầu với mã mới. Bạn có thể tiếp tục công việc khác và liên hệ quản trị viên.</p>}
            {content && !store.conflict.has(marker.request_id) && <div className={styles.replay}>
              <p>Nội dung ban đầu: {content.name}</p><p>{content.description}</p>
              <Checkbox checked={confirmed === marker.request_id} label="Tôi xác nhận gửi lại đúng nội dung ban đầu, cùng mã yêu cầu." onChange={(_, data) => setConfirmed(data.checked ? marker.request_id : null)} />
              <div className={styles.actions}><Button disabled={confirmed !== marker.request_id || store.busy.size > 0 || !!store.problem} onClick={() => { setConfirmed(null); void store.replay(marker.request_id); }}>Gửi lại yêu cầu ban đầu</Button></div>
            </div>}
            {!content && <p>Nội dung ban đầu không còn trong trang này. Chỉ kiểm tra kết quả; không nhập lại để gửi thay thế.</p>}
          </>}
          <div className={styles.actions}>
            {marker.phase === "COMMITTED" ? <Button onClick={() => { if (store.isActive()) onNavigate(projectPreliminaryIntakePath(marker.project_id!)); }}>Mở hồ sơ đã gắn với mã yêu cầu</Button> : <>
              <Button disabled={store.busy.size > 0} onClick={() => void store.check(marker.request_id)}>Kiểm tra kết quả</Button>
              <Button disabled={store.busy.size > 0} onClick={() => store.park(marker.request_id)}>Tạm gác và liên hệ hỗ trợ</Button>
            </>}
            <a className="valora-button valora-button--secondary" href={`data:application/json;charset=utf-8,${encodeURIComponent(store.recoveryHandle(marker))}`} download={`preliminary-recovery-${marker.request_id}.json`}>Tải mã khôi phục</a>
          </div>
        </section>;
      })}
    </div>
    <div className={`valora-panel__footer ${styles.actions}`}>
      <Button onClick={onSessionExpired}>Khôi phục phiên làm việc</Button>
      <Button onClick={() => onNavigate(APP_ROUTES.preliminaryRequestManagement)}>Tiếp tục công việc khác</Button>
    </div>
  </section>;
}
