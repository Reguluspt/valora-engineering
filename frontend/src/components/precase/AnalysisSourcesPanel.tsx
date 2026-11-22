import React, { useEffect, useId, useRef, useState } from "react";
import { Button, Input, Select, Textarea } from "@fluentui/react-components";
import { AnalysisNumberInput } from "./AnalysisNumberInput";
import { decodeSourceBackup, encodeSourceBackup } from "./analysisSourceDraftBackup";
import { formatAnalysisNumber, type AnalysisReference } from "./analysisPresentation";
import { draftUrlIssue, draftUrlTokens, sourceEvaluations, sourceHasUrlCredentials, sourceKinds, type SourceDraft, type useAnalysisSourceDrafts } from "./analysisSourceDrafts";

const urlMessages = {
  https: "Chỉ ghi nhận URL HTTPS hợp lệ.",
  credentials: "Hãy bỏ tài khoản, mật khẩu hoặc mã truy cập khỏi URL để lưu bản nháp.",
};

const saveFeedback = {
  session: { label: "Bản nháp · Chưa lưu", icon: "–" },
  incomplete: { label: "Chưa đủ Link và Giá khảo sát", icon: "–" },
  saving: { label: "Đang lưu…", icon: "◷" },
  saved: { label: "Đã lưu nháp trên thiết bị", icon: "✓" },
  failed: { label: "Lưu thất bại", icon: "!" },
};
const retryHint = "Sửa bản nháp để thử lưu lại.";

export function AnalysisSourcesPanel({ row, reference, drafts, actions, editable, fixture }: {
  row: number;
  reference?: AnalysisReference;
  drafts: SourceDraft[];
  actions: ReturnType<typeof useAnalysisSourceDrafts>;
  editable: boolean;
  fixture: boolean;
}) {
  editable = editable && !actions.loading;
  const [selected, setSelected] = useState<string | null>(null);
  const [urlEdit, setUrlEdit] = useState<{ id: string; value: string } | null>(null);
  const [backupStatus, setBackupStatus] = useState("");
  const previousCount = useRef(drafts.length);
  const editor = useRef<HTMLTextAreaElement>(null);
  const addButton = useRef<HTMLButtonElement>(null);
  const panelId = useId();
  useEffect(() => {
    if (drafts.length > previousCount.current) {
      setSelected(drafts[drafts.length - 1].id);
    }
    previousCount.current = drafts.length;
  }, [drafts]);
  useEffect(() => { if (selected) editor.current?.focus(); }, [selected]);
  const active = drafts.find(source => source.id === selected);
  const patch = (values: Partial<SourceDraft>) => { if (editable && active) actions.patch(row, active.id, values); };
  const changeNarrative = (narrative: string) => {
    if (!active) return;
    const previous = draftUrlTokens(active.narrative);
    const urls = draftUrlTokens(narrative).filter(url => !draftUrlIssue(url));
    const added = urls.filter(url => !previous.includes(url));
    const replace = !active.url || (previous.includes(active.url) && !urls.includes(active.url));
    const url = replace ? added[0] ?? "" : active.url;
    const pendingUrls = [...new Set([
      ...active.pendingUrls.filter(pending => !previous.includes(pending) || urls.includes(pending)),
      ...added,
    ])].filter(pending => pending !== url);
    patch({ narrative, url, pendingUrls, ...(url && url !== active.url && { kind: "internet_survey" }) });
  };
  const paste = (event: React.ClipboardEvent<HTMLTextAreaElement>) => {
    if (!editable || !active) return;
    const files = Array.from(event.clipboardData.items).filter(item => item.type.startsWith("image/")).map(item => item.getAsFile()).filter((file): file is File => Boolean(file));
    const text = event.clipboardData.getData("text/plain");
    const links = text.split(/\s+/).filter(Boolean);
    const urls = links.filter(link => !draftUrlIssue(link));
    if (files.length) { event.preventDefault(); actions.attach(row, active, files); }
    if (urls.length === links.length && urls.length) {
      event.preventDefault();
      if (!active.url) patch({ url: urls[0], kind: "internet_survey", pendingUrls: [...new Set(urls.filter(url => url !== urls[0]))], ...(!files.length && { error: "" }) });
      else patch({ pendingUrls: [...new Set(urls.filter(url => url !== active.url))], ...(!files.length && { error: "" }) });
    } else if (files.length && text) {
      const input = event.currentTarget;
      input.setRangeText(text, input.selectionStart, input.selectionEnd, "end");
      changeNarrative(input.value);
    }
  };
  return <section className="analysis-sources" aria-label="Nguồn giá tham khảo">
    <div className="analysis-sources-heading"><h3>NGUỒN GIÁ THAM KHẢO ({drafts.length + (reference ? 1 : 0)})</h3>
      <Button ref={addButton} appearance="secondary" disabled={!editable} onClick={() => actions.add(row)}>+ Thêm nguồn giá</Button></div>
    <p className="analysis-field-note" role="status">{drafts.length} bản nháp · {drafts.filter(source => source.evaluation !== "unreviewed" && !source.needsReview).length} đã đánh giá nháp · {reference ? 1 : 0} gợi ý · Nguồn đã đăng ký: chưa có dữ liệu trong giai đoạn này.</p>
    <p className="analysis-field-note">{actions.persistent ? "Bản nháp minh họa tự lưu trên thiết bị khi đủ Link và Giá khảo sát. Nguồn chưa được lưu vào hệ thống."
      : fixture ? "Bản nháp minh họa. Bản nháp chưa được lưu vào hệ thống; tải lại trang sẽ mất nội dung và ảnh."
        : "Chưa hỗ trợ lưu trong giai đoạn này. Thêm và đánh giá nguồn chỉ khả dụng trong bản minh họa local."}</p>
    {actions.loading && <p role="status">Đang đọc bản nháp trên thiết bị…</p>}
    {actions.unavailable && <p role="alert">Trình duyệt không mở được bộ nhớ bản nháp khi tải trang. Bạn có thể tiếp tục nhập và xem trạng thái lưu ở từng nguồn.</p>}

    {actions.scope && <details>
      <summary>Sao lưu nguồn nháp dạng văn bản</summary>
      <p className="analysis-field-note">Tệp sao lưu giữ Link, giá và diễn giải của tài sản này. Ảnh clipboard không có trong tệp sao lưu.</p>
      <Button appearance="subtle" disabled={!drafts.length} onClick={() => {
        const text = encodeSourceBackup(actions.scope!, row, drafts);
        if (text === null) { setBackupStatus("Chưa thể tải bản sao. Hãy bỏ thông tin đăng nhập khỏi URL trong bản nháp."); return; }
        const backup = new Blob([text], { type: "application/json" });
        if (backup.size > 2 * 1024 * 1024) { setBackupStatus("Tệp sao lưu vượt 2 MiB."); return; }
        const url = URL.createObjectURL(backup);
        const link = document.createElement("a");
        link.href = url;
        link.download = "valora-nguon-nhap.json";
        link.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
      }}>Tải bản sao nháp</Button>
      <label className="analysis-field"><span>Nhập bản sao của tài sản này</span><input type="file" accept=".json,application/json" disabled={!editable}
        onChange={async event => {
          const input = event.currentTarget;
          const file = input.files?.[0];
          if (!file) return;
          try {
            if (file.size > 2 * 1024 * 1024) throw new Error("Backup exceeds 2 MiB");
            actions.importDrafts(row, decodeSourceBackup(await file.text(), actions.scope!, row));
            setBackupStatus("Đã đọc bản sao vào phiên xem. Xem trạng thái tự lưu trên từng nguồn.");
          } catch { setBackupStatus("Không đọc được bản sao cho tài sản này."); }
          input.value = "";
        }} /></label>
      {backupStatus && <p role="status">{backupStatus}</p>}
    </details>}
    <p className="analysis-field-note">Ưu tiên: Internet → Thuyết minh đơn giá → Kết quả thẩm định hồ sơ cũ. Người dùng quyết định giá.</p>
    {reference && <article className="analysis-source-card" aria-label="Nguồn hệ thống gợi ý">
      <span className="analysis-status amber">HỆ THỐNG GỢI Ý · CHƯA XÁC MINH</span>
      <h4>{reference.name}</h4><p>{reference.kind} · {reference.date}</p>
      <div className="analysis-source-price"><span>Giá tại nguồn</span><strong>{formatAnalysisNumber(reference.price)} đ</strong></div>
      <div className="analysis-conditions"><span>VAT: {reference.vat}</span><span>VC: {reference.delivery}</span></div>
      <details><summary>Xem chi tiết gợi ý</summary><p>Chỉ là dữ liệu tham khảo minh họa, chưa đăng ký và chưa được chấp nhận cho tài sản này. Không có chứng cứ gốc để mở.</p></details>
    </article>}
    {!drafts.length && !reference && <p className="analysis-source-empty">Chưa có nguồn giá. Chọn + Thêm nguồn giá để tạo bản nháp minh họa.</p>}
    {drafts.map((source, index) => {
      const sourceName = "Nguồn giá " + String(index + 1).padStart(2, "0");
      const expanded = source.id === selected;
      const detailLabel = expanded ? "Thu gọn" : "Xem chi tiết";
      const editorId = panelId + "-" + source.id;
      const price = formatAnalysisNumber(source.price);
      const currency = source.currency.trim();
      const saveStatus = actions.statusFor(source);
      const capturedUrl = Boolean(source.url) && !draftUrlIssue(source.url);
      const urlHasCredentials = draftUrlIssue(source.url) === "credentials";
      const urlIssue = sourceHasUrlCredentials(source) ? "credentials"
        : (source.url && draftUrlIssue(source.url)) || draftUrlTokens(source.narrative).map(draftUrlIssue).find(Boolean);
      const editing = urlEdit?.id === source.id ? urlEdit : null;
      const editIssue = editing && draftUrlIssue(editing.value);
      const feedback = saveFeedback[saveStatus];
      const saveLabel = saveStatus === "incomplete" && urlIssue === "credentials" ? "Chưa lưu nháp" : feedback.label;
      const saveBadge = <span className="analysis-status analysis-source-save" data-save-status={saveStatus} id={editorId + "-save"}>
        <span className="analysis-source-save-icon" aria-hidden="true">{feedback.icon}</span>
        <span><span>{saveLabel}</span>{expanded && saveStatus === "failed" && <small>{retryHint}</small>}</span>
      </span>;

      return <article className="analysis-source-card analysis-source-draft" key={source.id} data-source-draft={source.id} aria-label={sourceName}>
        <div className="analysis-source-draft-heading">
          <h4>{sourceName}</h4>
          {!expanded && saveBadge}
        </div>
        <p>{sourceKinds[source.kind]}</p>
        <div className="analysis-source-price"><span>Giá khảo sát</span><strong>{price}{source.price.trim() && currency ? " " + currency : ""}</strong></div>
        <p>{sourceEvaluations[source.evaluation]}{source.needsReview ? " · Nội dung đã đổi, cần rà soát lại" : ""}</p>
        <p>{capturedUrl ? 1 : 0} URL · {source.images.length} ảnh chứng cứ</p>
        {capturedUrl && <p className="analysis-field-note">Cần xác minh nguồn. Chưa dùng làm chứng cứ giá.</p>}
        {urlIssue && <p id={editorId + "-url-status"} role="status">{urlMessages[urlIssue]}</p>}
        {expanded && <div className="analysis-source-editor" id={editorId}>
          <label className="analysis-field"><span>Loại nguồn</span><Select disabled={!editable} value={source.kind} onChange={(_, data) => patch({ kind: data.value as SourceDraft["kind"] })}>
            {Object.entries(sourceKinds).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</Select></label>
          <label className="analysis-field"><span>Diễn giải, URL hoặc ảnh clipboard</span><Textarea ref={editor} aria-label="Diễn giải, URL hoặc ảnh clipboard" disabled={!editable} rows={4} value={source.narrative}
            aria-describedby={urlIssue ? editorId + "-url-status" : undefined}
            onPaste={paste} onChange={(_, data) => changeNarrative(data.value)} placeholder="Nhập diễn giải nhiều đoạn hoặc Ctrl+V để dán URL HTTPS / ảnh" /></label>
          <p className="analysis-field-note">Diễn giải nháp riêng, không ghi vào cơ sở giá 64 ký tự. Không tải website hoặc upload ảnh.</p>
          {source.url && <>
            <div className="analysis-url-chip"><span>{capturedUrl ? "Đã ghi nhận URL" : "URL cũ trong bản nháp"}</span>{!urlHasCredentials && <code>{source.url}</code>}
              <Button disabled={!editable || Boolean(editing)} onClick={() => setUrlEdit({ id: source.id, value: urlHasCredentials ? "" : source.url })}>Sửa URL</Button>
              <Button disabled={!editable} onClick={() => { setUrlEdit(null); patch({ url: "" }); }}>Bỏ URL</Button>
            </div>
            <p className="analysis-field-note">Kiểm tra dấu câu trên URL nháp. Dùng &lt; và &gt; để tách URL khỏi dấu câu trong diễn giải.</p>
            {editing && <>
              <label className="analysis-field"><span>URL của nguồn</span><Input autoFocus disabled={!editable} value={editing.value}
                aria-describedby={editIssue ? editorId + "-url-edit-status" : undefined}
                onChange={(_, data) => setUrlEdit({ id: source.id, value: data.value })} /></label>
              {editIssue && <p id={editorId + "-url-edit-status"} role="status">{urlMessages[editIssue]}</p>}
              <Button disabled={!editable || Boolean(editIssue)} onClick={() => {
                if (editing.value !== source.url) patch({ url: editing.value, pendingUrls: source.pendingUrls.filter(url => url !== editing.value) });
                setUrlEdit(null);
              }}>Áp dụng URL</Button>
              <Button onClick={() => setUrlEdit(null)}>Hủy sửa URL</Button>
            </>}
          </>}
          {source.pendingUrls.length > 0 && <div className="analysis-url-conflict" role="group" aria-label="Xử lý URL mới">
            <p>URL mới: <code>{source.pendingUrls[0]}</code>. Chọn tạo nguồn riêng hoặc thay link hiện tại.</p>
            <Button disabled={!editable} onClick={() => { actions.add(row, source.pendingUrls[0]); patch({ pendingUrls: source.pendingUrls.slice(1) }); }}>Tạo nguồn mới với URL này</Button>
            <Button disabled={!editable} onClick={() => patch({ url: source.pendingUrls[0], pendingUrls: source.pendingUrls.slice(1), kind: "internet_survey" })}>Thay link hiện tại</Button>
            <Button disabled={!editable} onClick={() => patch({ pendingUrls: [] })}>Giữ link hiện tại</Button>
          </div>}
          {source.images.map((image, imageIndex) => <figure className="analysis-image-draft" key={image.id}><img src={image.url} alt={`Ảnh chứng cứ nháp ${imageIndex + 1}`} />
            <figcaption>Ảnh clipboard · {actions.persistent ? (saveStatus === "saved" ? "đã lưu trên thiết bị" : "chưa xác minh lưu trên thiết bị") : "chưa upload"} <Button disabled={!editable} onClick={() => actions.removeImage(row, source, image.id)}>Xóa ảnh {imageIndex + 1}</Button></figcaption></figure>)}
          {source.error && <p role="alert">{source.error}</p>}
          <div className="analysis-source-price-entry">
            <label className="analysis-field"><span>Giá khảo sát</span><AnalysisNumberInput disabled={!editable} aria-label="Giá khảo sát" aria-describedby={editorId + "-save"}
              value={source.price} onChange={price => patch({ price })} /></label>
            {saveBadge}
            <span className="analysis-sr-only analysis-source-save-announcement" role="status">
              {saveStatus === "saved" ? saveLabel : saveStatus === "failed" ? saveLabel + ". " + retryHint : ""}
            </span>
          </div>
          {([["VAT", "vat"], ["Vận chuyển", "delivery"]] as const).map(([label, field]) => <label className="analysis-field" key={field}><span>{label}</span><Select disabled={!editable} value={source[field]} onChange={(_, data) => patch({ [field]: data.value })}>
            <option>Chưa xác định</option><option>Đã bao gồm</option><option>Chưa bao gồm</option></Select></label>)}
          <label className="analysis-field"><span>Đánh giá riêng cho tài sản này (nháp)</span><Select disabled={!editable} value={source.evaluation} onChange={(_, data) => patch({ evaluation: data.value as SourceDraft["evaluation"], needsReview: false })}>
            {Object.entries(sourceEvaluations).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</Select></label>
          <p className="analysis-field-note">Quyết định minh họa chưa được server xác nhận. Đơn giá đề xuất được giữ nguyên.</p>
        </div>}
        <div className="analysis-source-draft-actions">
          <Button appearance="subtle" size="small" aria-expanded={expanded} aria-controls={expanded ? editorId : undefined}
            aria-label={detailLabel + " " + sourceName.toLowerCase()} onClick={() => setSelected(expanded ? null : source.id)}
            icon={<svg viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false"><path d={expanded ? "m4 10 4-4 4 4" : "m4 6 4 4 4-4"} /></svg>}>
            {detailLabel}
          </Button>
          <Button appearance="subtle" size="small" aria-label={"Xóa bản nháp " + sourceName.toLowerCase()} disabled={!editable}
            onClick={() => { actions.remove(row, source.id); if (expanded) setSelected(null); addButton.current?.focus(); }}>
            Xóa bản nháp
          </Button>
        </div>
      </article>;
    })}
  </section>;
}
