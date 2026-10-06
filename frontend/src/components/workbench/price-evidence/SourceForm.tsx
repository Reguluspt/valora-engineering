import { useState } from "react";
import { Button, Checkbox, Field, Select } from "@fluentui/react-components";
import type { EvidenceCategory, EvidenceSourceView, ObservedValue, SourceMaterial } from "../../../api/priceEvidence";
import { EvidenceField, categoryLabels, localInput, utcInput } from "./EvidenceFields";
import { HistoricalSourceSelector } from "./HistoricalSourceSelector";

const emptyValue: ObservedValue = { amount: "", range_upper: null, currency: "", unit_basis: "", quantity_basis: "",
  tax: "", delivery: "", condition: "", locator: "" };
const labels: Record<keyof ObservedValue, string> = { amount: "Giá trị ghi nhận", range_upper: "Giới hạn trên của khoảng giá (nếu có)",
  currency: "Mã tiền tệ (3 chữ hoa)", unit_basis: "Đơn vị tính", quantity_basis: "Cơ sở số lượng", tax: "Thuế",
  delivery: "Giao hàng", condition: "Tình trạng tài sản nguồn", locator: "Vị trí giá trị trong nguồn" };
export function SourceForm({ projectId, initial, sources, moreSources, onMore, onSave, onCancel }: {
  projectId: string; initial?: SourceMaterial; sources: EvidenceSourceView[]; moreSources: boolean; onMore: () => void;
  onSave: (material: SourceMaterial, reason: string) => void; onCancel: () => void;
}) {
  const [category, setCategory] = useState<EvidenceCategory>(initial?.category || "internet_survey");
  const [origin, setOrigin] = useState(initial?.origin || ""), [reference, setReference] = useState(initial?.reference || "");
  const [locator, setLocator] = useState(initial?.locator || ""), [date, setDate] = useState(initial?.effective_date || "");
  const [unknown, setUnknown] = useState(initial?.unknown_date_reason || ""), [capture, setCapture] = useState(localInput(initial?.captured_at || null));
  const [text, setText] = useState(initial?.retained_text || ""), [limitations, setLimitations] = useState(initial?.limitations || "");
  const [expiry, setExpiry] = useState(localInput(initial?.expires_at || null)), [value, setValue] = useState(initial?.value || emptyValue);
  const [hasValue, setHasValue] = useState(Boolean(initial?.value ?? true));
  const [inputs, setInputs] = useState(initial?.explanation?.inputs || [{ evidence_revision_id: "", coefficient: "" }]);
  const [assumptions, setAssumptions] = useState(initial?.explanation?.assumptions || ""), [calculations, setCalculations] = useState(initial?.explanation?.calculations || "");
  const [priorProject, setPriorProject] = useState(initial?.historical?.project_id || ""), [priorLine, setPriorLine] = useState(initial?.historical?.line_id || "");
  const [excerpt, setExcerpt] = useState(initial?.historical?.result_excerpt || ""), [resultLocator, setResultLocator] = useState(initial?.historical?.result_locator || "");
  const [reason, setReason] = useState(""), [error, setError] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const valued = category !== "internet_survey" || hasValue;
  const save = () => {
    setError("");
    const decimals = [value.amount, value.quantity_basis, ...(value.range_upper ? [value.range_upper] : []),
      ...(category === "unit_price_explanation" ? inputs.map(i => i.coefficient) : [])];
    if (valued && decimals.some(v => !/^(?:0|[1-9][0-9]{0,17})(?:\.[0-9]{1,8})?$/.test(v))) {
      setError("Nhập số thập phân chính xác bằng dấu chấm, không dùng dấu phân cách hàng nghìn. Tối đa 18 chữ số nguyên và 8 chữ số thập phân."); return;
    }
    if (valued && !/^[A-Z]{3}$/.test(value.currency)) { setError("Mã tiền tệ cần đúng 3 chữ cái viết hoa."); return; }
    if (text.trim().length < 20 || (category === "prior_appraisal_result" && excerpt.trim().length < 20)) {
      setError("Nội dung lưu giữ và trích đoạn kết quả cần ít nhất 20 ký tự có nghĩa."); return;
    }
    if (category === "unit_price_explanation" && new Set(inputs.map(i => i.evidence_revision_id)).size !== inputs.length) {
      setError("Mỗi nguồn đầu vào chỉ được chọn một lần."); return;
    }
    try {
      onSave({ category, origin, reference: reference || null, locator, effective_date: date || null,
        unknown_date_reason: date ? null : unknown, captured_at: utcInput(capture)!,
        capture_method: category === "unit_price_explanation" ? "authored_explanation" : "manual_transcription",
        retained_text: text, limitations, expires_at: utcInput(expiry), value: valued ? value : null,
        explanation: category === "unit_price_explanation" ? { method: "sum_of_scaled_source_values", inputs, assumptions,
          calculations, units: value.unit_basis, currency: value.currency, proposed_basis_value: value.amount } : null,
        historical: category === "prior_appraisal_result" ? { project_id: priorProject, line_id: priorLine, appraisal_date: date,
          result_excerpt: excerpt, result_locator: resultLocator, result_value: value } : null,
      }, reason);
    } catch { setError("Kiểm tra ngày và thời điểm trước khi xác nhận."); }
  };
  return <form onSubmit={event => { event.preventDefault(); save(); }} className="valora-form">
    <p>Nội dung do người dùng nhập và lưu giữ thủ công. VALORA không tải hoặc xác minh nội dung từ đường dẫn.</p>
    <Field label="Loại nguồn" required><Select value={category} onChange={(_, data) => setCategory(data.value as EvidenceCategory)}>
      {Object.entries(categoryLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
    </Select></Field>
    <EvidenceField label="Nhà xuất bản / tác giả / nguồn gốc" value={origin} onChange={setOrigin} />
    <EvidenceField label="Tham chiếu HTTPS công khai" value={reference} onChange={setReference} required={category === "internet_survey"} />
    <p>Đường dẫn chỉ dùng tham chiếu; không có tài khoản, mật khẩu, chuỗi truy vấn hay phần neo.</p>
    <EvidenceField label="Vị trí nguồn (trang, mục, dòng)" value={locator} onChange={setLocator} />
    {category === "prior_appraisal_result" && <HistoricalSourceSelector projectId={projectId} selectedProject={priorProject}
      selectedLine={priorLine} onProject={setPriorProject} onLine={setPriorLine} />}
    <EvidenceField label={category === "prior_appraisal_result" ? "Ngày thẩm định trước" : "Ngày nguồn / ngày hiệu lực"}
      type="date" value={date} onChange={setDate} required={category === "prior_appraisal_result"} />
    {!date && category !== "prior_appraisal_result" && <EvidenceField label="Lý do không xác định được ngày nguồn" value={unknown} onChange={setUnknown} />}
    <EvidenceField label="Thời điểm quan sát / ghi nhận (giờ địa phương)" type="datetime-local" value={capture} onChange={setCapture} />
    <EvidenceField label="Nội dung văn bản lưu giữ" multiline value={text} onChange={setText} limit={20000} />
    <EvidenceField label="Hạn chế của nguồn" multiline value={limitations} onChange={setLimitations} />
    <EvidenceField label="Hết hạn nguồn (giờ địa phương, nếu có)" type="datetime-local" value={expiry} onChange={setExpiry} required={false} />
    {category === "internet_survey" && <Checkbox label="Nguồn có giá trị quan sát được" checked={hasValue} onChange={(_, data) => setHasValue(data.checked === true)} />}
    {!valued && <p>Nguồn không có giá trị không thể tự đáp ứng điều kiện làm cơ sở giá.</p>}
    {valued && <fieldset><legend>{category === "prior_appraisal_result" ? "Giá trị kết quả thẩm định trước" : category === "unit_price_explanation" ? "Giá trị cơ sở đề xuất" : "Giá trị theo nguồn"}</legend>
      {(Object.keys(labels) as (keyof ObservedValue)[]).filter(key => category !== "unit_price_explanation" || key !== "range_upper").map(key =>
        <EvidenceField key={key} label={labels[key]} value={value[key] || ""} required={key !== "range_upper"}
          onChange={next => setValue(v => ({ ...v, [key]: key === "range_upper" ? next || null : next }))} />)}
      <p>Số thập phân dùng dấu chấm. Không tự quy đổi tiền tệ, thuế hay đơn vị.</p>
    </fieldset>}
    {category === "unit_price_explanation" && <fieldset><legend>Giải trình có cấu trúc</legend>
      <p>Phương pháp: tổng giá trị các nguồn nhân hệ số. Hệ thống kiểm tra phép tính chính xác; người dùng đánh giá tính phù hợp.</p>
      {inputs.map((input, index) => <div key={index}>
        <Field label={`Nguồn đầu vào ${index + 1}`} required><Select required value={input.evidence_revision_id}
          onChange={(_, data) => setInputs(items => items.map((item, i) => i === index ? { ...item, evidence_revision_id: data.value } : item))}>
          <option value="">Chọn nguồn đã đăng ký</option>{sources.filter(s => s.explanation_input_eligible).map(s =>
            <option key={s.evidence_revision_id} value={s.evidence_revision_id}>{s.origin} · Phiên bản {s.revision}</option>)}
        </Select></Field>
        <EvidenceField label={`Hệ số nguồn ${index + 1}`} value={input.coefficient}
          onChange={next => setInputs(items => items.map((item, i) => i === index ? { ...item, coefficient: next } : item))} />
        {inputs.length > 1 && <Button onClick={() => setInputs(items => items.filter((_, i) => i !== index))}>Bỏ đầu vào {index + 1}</Button>}
      </div>)}
      {inputs.length < 50 && <Button onClick={() => setInputs(items => [...items, { evidence_revision_id: "", coefficient: "" }])}>Thêm nguồn đầu vào</Button>}
      {moreSources && <Button onClick={onMore}>Tải thêm nguồn đã đăng ký</Button>}
      <EvidenceField label="Giả định" multiline value={assumptions} onChange={setAssumptions} />
      <EvidenceField label="Phép tính và diễn giải" multiline value={calculations} onChange={setCalculations} />
    </fieldset>}
    {category === "prior_appraisal_result" && <>
      <EvidenceField label="Trích đoạn kết quả thẩm định trước" multiline value={excerpt} onChange={setExcerpt} limit={20000} />
      <EvidenceField label="Vị trí kết quả thẩm định trước" value={resultLocator} onChange={setResultLocator} />
      <p>Trích đoạn phải thuộc kết quả thẩm định trước; báo giá nhà cung cấp không thay thế kết quả này.</p>
    </>}
    {initial && <EvidenceField label="Lý do tạo phiên bản thay thế" multiline value={reason} onChange={setReason} />}
    <Checkbox label={initial ? "Tôi xác nhận tạo phiên bản nguồn thay thế; lịch sử được giữ nguyên" : "Tôi xác nhận đăng ký nội dung nguồn đã kiểm tra"}
      checked={confirmed} onChange={(_, data) => setConfirmed(data.checked === true)} />
    {error && <p role="alert">{error}</p>}
    <div className="asset-review-actions"><Button onClick={onCancel}>Hủy</Button>
      <Button type="submit" appearance="primary" disabled={!confirmed}>Xác nhận đăng ký nguồn</Button></div>
  </form>;
}
