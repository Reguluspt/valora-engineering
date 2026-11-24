import React, { useId, useLayoutEffect, useRef, useState } from "react";
import { Input, type InputProps } from "@fluentui/react-components";
import { analysisNumberCaret, formatAnalysisNumber, parseAnalysisNumberInput } from "./analysisPresentation";

export function AnalysisNumberInput({ value, onChange, onFocus, onKeyDown, ...props }: Omit<InputProps, "value" | "onChange" | "onFocus" | "onBlur"> & {
  value: string;
  onChange: (value: string) => void;
  onFocus?: () => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const composing = useRef(false);
  const [composition, setComposition] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [selection, setSelection] = useState<{ start: number; end: number; direction: "forward" | "backward" | "none" } | null>(null);
  const errorId = useId();
  const display = formatAnalysisNumber(value, "");

  useLayoutEffect(() => {
    if (selection) input.current?.setSelectionRange(selection.start, selection.end, selection.direction);
  }, [selection]);

  const accept = (text: string, start = text.length, end = start, direction: "forward" | "backward" | "none" = "none") => {
    if (props.disabled || props.readOnly) return;
    const raw = parseAnalysisNumberInput(text);
    if (raw === null) {
      setError("Chưa áp dụng dữ liệu nhập. Dùng dấu chấm phân cách hàng nghìn và dấu phẩy cho phần thập phân, ví dụ 92.400.000 hoặc 5,25.");
      setSelection({ start: Math.min(start, display.length), end: Math.min(end, display.length), direction });
      return;
    }
    const formatted = formatAnalysisNumber(raw, "");
    setError("");
    setSelection({ start: analysisNumberCaret(text, start, formatted), end: analysisNumberCaret(text, end, formatted), direction });
    if (raw !== value) onChange(raw);
  };

  return <div className="analysis-number-field"><Input {...props} input={{ ref: input }} type="text" value={composition ?? display}
    aria-invalid={Boolean(error) || props["aria-invalid"]}
    aria-describedby={[props["aria-describedby"], error ? errorId : ""].filter(Boolean).join(" ") || undefined}
    onFocus={() => onFocus?.()}
    onCompositionStart={() => { composing.current = true; setComposition(display); }}
    onCompositionEnd={(event) => {
      composing.current = false;
      setComposition(null);
      const target = event.target as HTMLInputElement;
      accept(target.value, target.selectionStart ?? target.value.length, target.selectionEnd ?? target.value.length);
    }}
    onBlur={() => { composing.current = false; setComposition(null); }}
    onKeyDown={(event) => {
      onKeyDown?.(event);
      if (event.defaultPrevented || event.ctrlKey || event.metaKey || event.altKey || composing.current) return;
      const target = event.target as HTMLInputElement;
      const start = target.selectionStart, end = target.selectionEnd;
      if (start === null || start !== end) return;
      const index = event.key === "Backspace" && display[start - 1] === "." ? start - 2
        : event.key === "Delete" && display[start] === "." ? start + 1 : -1;
      if (index < 0) return;
      event.preventDefault();
      const ungrouped = display.slice(0, index) + display.slice(index + 1);
      const caret = event.key === "Backspace" ? start - 1 : start;
      const rawDisplay = ungrouped.replace(/\./g, "");
      const rawCaret = ungrouped.slice(0, caret).replace(/\./g, "").length;
      accept(rawDisplay, rawCaret);
    }}
    onChange={(event, data) => {
      const target = event.target as HTMLInputElement;
      if (composing.current) { setComposition(data.value); return; }
      const native = event.nativeEvent as InputEvent;
      const start = target.selectionStart ?? data.value.length, end = target.selectionEnd ?? start;
      if (native?.data === ".") { accept(".", Math.max(0, start - 1)); return; }
      const text = data.value.replace(/\./g, "");
      accept(text, data.value.slice(0, start).replace(/\./g, "").length,
        data.value.slice(0, end).replace(/\./g, "").length, target.selectionDirection ?? "none");
    }}
    onPaste={(event) => {
      if (props.disabled || props.readOnly) return;
      event.preventDefault();
      const target = event.target as HTMLInputElement;
      const pasted = event.clipboardData.getData("text/plain").trim();
      const start = target.selectionStart ?? 0, end = target.selectionEnd ?? start;
      if (parseAnalysisNumberInput(pasted) === null) { accept(pasted, start, end, target.selectionDirection ?? "none"); return; }
      const prefix = display.slice(0, start).replace(/\./g, "");
      const text = prefix + pasted.replace(/\./g, "") + display.slice(end).replace(/\./g, "");
      accept(text, prefix.length + pasted.replace(/\./g, "").length);
    }} />
    {error && <span id={errorId} className="analysis-input-feedback" role="alert">{error}</span>}
  </div>;
}
