import { Field, Input, Textarea } from "@fluentui/react-components";

export function EvidenceField({ label, value, onChange, required = true, multiline = false, type = "text", limit = 2000 }: {
  label: string; value: string; onChange: (value: string) => void; required?: boolean; multiline?: boolean;
  type?: "text" | "date" | "datetime-local"; limit?: number;
}) {
  const tooLong = [...value.trim()].length > limit;
  return <Field label={label} required={required} validationState={tooLong ? "error" : "none"}
    validationMessage={tooLong ? `Tối đa ${limit} ký tự.` : undefined}>
    {multiline ? <Textarea value={value} required={required} onChange={(_, data) => onChange(data.value)} />
      : <Input type={type} value={value} required={required} onChange={(_, data) => onChange(data.value)} />}
  </Field>;
}
export const categoryLabels = {
  internet_survey: "Khảo sát Internet", unit_price_explanation: "Giải trình đơn giá", prior_appraisal_result: "Kết quả thẩm định trước",
};
export const utcInput = (value: string) => value ? new Date(value).toISOString() : null;
export function localInput(value: string | null) {
  if (!value) return "";
  const date = new Date(value);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}
