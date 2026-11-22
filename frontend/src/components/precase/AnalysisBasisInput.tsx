import React, { useEffect, useId, useRef, useState } from "react";
import { Textarea, type TextareaProps } from "@fluentui/react-components";

export function AnalysisBasisInput({ value, onChange, autoResize = false, ...props }: Omit<TextareaProps, "value" | "onChange"> & {
  value: string;
  onChange: (value: string) => void;
  autoResize?: boolean;
}) {
  const textarea = useRef<HTMLTextAreaElement>(null);
  const feedbackId = useId();
  const [rejected, setRejected] = useState(false);
  const limit = 64;
  useEffect(() => {
    if (autoResize && textarea.current) {
      textarea.current.style.height = "auto";
      textarea.current.style.height = `${textarea.current.scrollHeight}px`;
    }
  }, [autoResize, value]);
  const exceedsLimit = (target: HTMLTextAreaElement, insertion: string) => value.length - (target.selectionEnd - target.selectionStart) + insertion.length > limit;
  return <><Textarea {...props} textarea={{ ref: textarea }} value={value} maxLength={limit}
    aria-describedby={[props["aria-describedby"], feedbackId].filter(Boolean).join(" ")}
    onPaste={(event) => {
      if (exceedsLimit(event.target as HTMLTextAreaElement, event.clipboardData.getData("text/plain"))) {
        event.preventDefault();
        setRejected(true);
      } else setRejected(false);
    }}
    onBeforeInput={(event) => {
      const data = (event.nativeEvent as InputEvent).data;
      if (data && exceedsLimit(event.target as HTMLTextAreaElement, data)) {
        event.preventDefault();
        setRejected(true);
      }
    }}
    onChange={(_, data) => {
      if (props.disabled || props.readOnly) return;
      if (data.value.length > limit) { setRejected(true); return; }
      setRejected(false);
      onChange(data.value);
    }} />
    <span id={feedbackId} className="analysis-basis-feedback" role="status" aria-live="polite">
      <span>{value.length}/{limit}</span>{rejected ? " · Vượt giới hạn 64 ký tự. Nội dung chưa được áp dụng; hãy rút ngắn rồi nhập lại." : value.length === limit ? " · Đã đạt giới hạn 64 ký tự." : " · Tối đa 64 ký tự."}
    </span>
  </>;
}
