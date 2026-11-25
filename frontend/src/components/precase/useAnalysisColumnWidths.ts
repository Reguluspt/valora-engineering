import { useEffect, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";

export const analysisColumns = [
  { id: "index", label: "STT", initial: 47, min: 42 },
  { id: "asset", label: "Tài sản", initial: 231, min: 120 },
  { id: "specs", label: "Đặc điểm", initial: 241, min: 120 },
  { id: "unit", label: "ĐVT", initial: 61, min: 52 },
  { id: "quantity", label: "SL nguồn", initial: 89, min: 76 },
  { id: "customer-price", label: "Đơn giá KH", initial: 142, min: 120 },
  { id: "customer-amount", label: "Thành tiền KH", initial: 160, min: 128 },
  { id: "survey", label: "Giá khảo sát", initial: 144, min: 120 },
  { id: "proposal", label: "Đơn giá đề xuất", initial: 159, min: 128 },
  { id: "amount", label: "Thành tiền đề xuất", initial: 167, min: 128 },
  { id: "sources", label: "Nguồn", initial: 77, min: 70 },
  { id: "evidence", label: "Chứng cứ", initial: 90, min: 78 },
  { id: "status", label: "Trạng thái", initial: 161, min: 108 },
] as const;

type Column = typeof analysisColumns[number];
type ColumnId = Column["id"];
type Widths = Partial<Record<ColumnId, number>>;

const DEFAULT_WIDTH = analysisColumns.reduce((sum, column) => sum + column.initial, 0);
const MAX_WIDTH = 4096;
const STEP = 8;
const PREFERENCE_KEY = "valora.ui.analysis.columnWidths.v1";

function readWidths(): Widths {
  try {
    const saved = JSON.parse(window.localStorage.getItem(PREFERENCE_KEY) ?? "{}");
    const widths: Widths = {};
    for (const column of analysisColumns) {
      const width = saved?.[column.id];
      if (Number.isInteger(width) && width >= column.min && width <= MAX_WIDTH) widths[column.id] = width;
    }
    return widths;
  } catch {
    return {};
  }
}

function limitWidth(column: Column, width: number) {
  return Math.min(MAX_WIDTH, Math.max(column.min, Math.round(width)));
}

export function useAnalysisColumnWidths(hasRows: boolean) {
  const tableRef = useRef<HTMLDivElement>(null);
  const drag = useRef<{ id: ColumnId; pointerId: number; x: number; width: number } | null>(null);
  const [availableWidth, setAvailableWidth] = useState(0);
  const [saved, setSaved] = useState(readWidths);
  const [preview, setPreview] = useState<{ id: ColumnId; width: number } | null>(null);

  useEffect(() => {
    const element = tableRef.current;
    if (!element) return;
    const measure = () => setAvailableWidth(element.clientWidth);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [hasRows]);

  const manual = preview ? { ...saved, [preview.id]: preview.width } : saved;
  const scale = Math.max(1, availableWidth / DEFAULT_WIDTH);
  const widths = analysisColumns.map((column) => manual[column.id] ?? Math.floor(column.initial * scale));
  const width = widths.reduce((total, size) => total + size, 0);
  // Grow only past the last adjusted column so its divider can follow the pointer.
  const extra = manual.status === undefined ? Math.max(0, availableWidth - width) : 0;
  widths[widths.length - 1] += extra;

  const update = (next: Widths) => {
    setSaved(next);
    try {
      if (Object.keys(next).length) window.localStorage.setItem(PREFERENCE_KEY, JSON.stringify(next));
      else window.localStorage.removeItem(PREFERENCE_KEY);
    } catch {
      // Column resizing remains usable when browser preferences are unavailable.
    }
  };

  const dragWidth = (event: PointerEvent, column: Column) => {
    const active = drag.current;
    if (active?.pointerId === event.pointerId && active.id === column.id) {
      return limitWidth(column, active.width + event.clientX - active.x);
    }
  };

  const handleProps = (column: Column, index: number) => ({
    role: "separator",
    tabIndex: 0,
    "aria-orientation": "vertical" as const,
    "aria-label": `Đổi độ rộng cột ${column.label}`,
    "aria-valuemin": column.min,
    "aria-valuemax": Math.max(MAX_WIDTH, Math.round(widths[index])),
    "aria-valuenow": Math.round(widths[index]),
    onPointerDown(event: PointerEvent<HTMLSpanElement>) {
      if (!event.isPrimary || event.button !== 0 || drag.current) return;
      const width = event.currentTarget.closest("th")!.getBoundingClientRect().width;
      drag.current = { id: column.id, pointerId: event.pointerId, x: event.clientX, width };
      event.currentTarget.setPointerCapture(event.pointerId);
      event.preventDefault();
    },
    onPointerMove(event: PointerEvent<HTMLSpanElement>) {
      const width = dragWidth(event, column);
      if (width !== undefined) setPreview({ id: column.id, width });
    },
    onPointerUp(event: PointerEvent<HTMLSpanElement>) {
      const width = dragWidth(event, column);
      if (width === undefined) return;
      if (event.clientX !== drag.current?.x) update({ ...saved, [column.id]: width });
      drag.current = null;
      setPreview(null);
    },
    onLostPointerCapture(event: PointerEvent<HTMLSpanElement>) {
      if (drag.current?.pointerId !== event.pointerId) return;
      drag.current = null;
      setPreview(null);
    },
    onKeyDown(event: KeyboardEvent<HTMLSpanElement>) {
      if (drag.current || (event.key !== "ArrowLeft" && event.key !== "ArrowRight")) return;
      event.preventDefault();
      const direction = event.key === "ArrowLeft" ? -1 : 1;
      update({ ...saved, [column.id]: limitWidth(column, widths[index] + direction * STEP) });
    },
  });

  return { tableRef, availableWidth, widths, width: width + extra, handleProps, resizing: preview !== null,
    canReset: Object.keys(saved).length > 0, reset: () => update({}) };
}
