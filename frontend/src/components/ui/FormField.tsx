import { Field, Input, Textarea, Select } from "@fluentui/react-components";

export function FormField({ label, value, onChange, required = true, multiline = false, type = "text", error, disabled = false }: {
  label: string; value: string; onChange: (value: string) => void; required?: boolean; multiline?: boolean;
  type?: "text" | "date" | "datetime-local"; error?: string; disabled?: boolean;
}) {
  return <Field label={label} required={required} validationState={error ? "error" : "none"} validationMessage={error}>
    {multiline ? <Textarea value={value} required={required} disabled={disabled} onChange={(_, d) => onChange(d.value)} />
      : <Input type={type} value={value} required={required} disabled={disabled} onChange={(_, d) => onChange(d.value)} />}
  </Field>;
}
export function SelectField({ label, value, onChange, options, disabled = false, required = true }: {
  label: string; value: string; onChange: (value: string) => void;
  options: { value: string; label: string; disabled?: boolean }[]; disabled?: boolean; required?: boolean;
}) {
  return <Field label={label} required={required}><Select value={value} required={required} disabled={disabled}
    onChange={(_, d) => onChange(d.value)}><option value="">Chọn…</option>
    {options.map(o => <option key={o.value} value={o.value} disabled={o.disabled}>{o.label}</option>)}</Select></Field>;
}
