import { useState } from "react";
import { Button, Checkbox, Field, Select } from "@fluentui/react-components";
import type { EvidenceSourceView, RelevanceFacts } from "../../../api/priceEvidence";
import { EvidenceField, utcInput } from "./EvidenceFields";

const textFields = {
  source_portion: "Phần nguồn liên quan", relevance_rationale: "Lý do liên quan đến tài sản đang chọn",
  suitability_rationale: "Lý do phù hợp làm cơ sở", limitations: "Hạn chế khi áp dụng",
  temporal_applicability: "Tính phù hợp theo thời gian", source_priority_rationale: "Lý do lựa chọn thứ tự ưu tiên nguồn",
};
export function RelevanceForm({ source, lineLabel, onSave, onCancel }: {
  source: EvidenceSourceView; lineLabel: string; onSave: (facts: RelevanceFacts, reason: string) => void; onCancel: () => void;
}) {
  const [fields, setFields] = useState(Object.fromEntries(Object.keys(textFields).map(k => [k, ""])) as Record<keyof typeof textFields, string>);
  const [disposition, setDisposition] = useState<RelevanceFacts["disposition"]>(source.can_accept ? "qualifying_basis" : "excluded_alternative");
  const [date, setDate] = useState(""), [deadline, setDeadline] = useState(""), [reason, setReason] = useState("");
  const [survey, setSurvey] = useState(false), [explanation, setExplanation] = useState(false), [confirmed, setConfirmed] = useState(false);
  const requiredReason = Boolean(source.decision) || disposition !== "qualifying_basis";
  const needsSurvey = source.category !== "internet_survey", needsExplanation = source.category === "prior_appraisal_result";
  return <form className="valora-form" onSubmit={event => {
    event.preventDefault();
    onSave({ ...fields, outcome: disposition === "qualifying_basis" ? "accepted" : "rejected", disposition,
      applicability_date: date, review_due_at: utcInput(deadline)!,
      higher_priorities_considered: [...(needsSurvey && survey ? ["internet_survey" as const] : []),
        ...(needsExplanation && explanation ? ["unit_price_explanation" as const] : [])],
    }, requiredReason ? reason : "");
  }}>
    <p>Phạm vi: {lineLabel} · {source.origin} · Phiên bản {source.revision}. Quyết định này chỉ áp dụng cho dòng tài sản đang chọn.</p>
    <Field label="Quyết định phù hợp" required><Select value={disposition} onChange={(_, data) => setDisposition(data.value as RelevanceFacts["disposition"])}>
      {source.can_accept && <option value="qualifying_basis">Chấp nhận làm cơ sở</option>}
      {source.can_reject && <><option value="excluded_alternative">Loại khỏi cơ sở</option><option value="unresolved_concern">Còn mâu thuẫn cần xử lý</option></>}
    </Select></Field>
    {Object.entries(textFields).map(([key, label]) => <EvidenceField key={key} label={label} multiline value={fields[key as keyof typeof fields]}
      onChange={value => setFields(previous => ({ ...previous, [key]: value }))} />)}
    <EvidenceField label="Ngày áp dụng" type="date" value={date} onChange={setDate} />
    <EvidenceField label="Hạn rà soát lại (giờ địa phương)" type="datetime-local" value={deadline} onChange={setDeadline} />
    {source.expires_at && <p>Hạn nguồn: {new Date(source.expires_at).toLocaleString("vi-VN")}. Hạn rà soát chấp nhận không được vượt hạn nguồn.</p>}
    {needsSurvey && <Checkbox label="Tôi đã xem xét nguồn khảo sát Internet có ưu tiên cao hơn" checked={survey} onChange={(_, data) => setSurvey(data.checked === true)} />}
    {needsExplanation && <Checkbox label="Tôi đã xem xét giải trình đơn giá có ưu tiên cao hơn" checked={explanation} onChange={(_, data) => setExplanation(data.checked === true)} />}
    {requiredReason && <EvidenceField label="Lý do quyết định / thay thế quyết định trước" multiline value={reason} onChange={setReason} />}
    <Checkbox label="Tôi xác nhận quyết định cho đúng nguồn và dòng tài sản này" checked={confirmed} onChange={(_, data) => setConfirmed(data.checked === true)} />
    <div className="asset-review-actions"><Button onClick={onCancel}>Hủy</Button>
      <Button type="submit" appearance="primary" disabled={!confirmed || needsSurvey && !survey || needsExplanation && !explanation}>Xác nhận quyết định</Button></div>
  </form>;
}
