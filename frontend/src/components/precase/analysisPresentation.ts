import type { ProjectAssetImportStagingRowResponse } from "../../api/assetImports";
import type { AnalysisDraft } from "./analysisReviewModel";

export interface AnalysisReference {
  name: string;
  kind: string;
  date: string;
  price: string;
  vat: string;
  delivery: string;
}

export interface AnalysisAssetPresentation {
  code: string;
  status: string;
  statusTone: "amber" | "blue" | "green" | "gray";
  viewed: boolean;
  manual: boolean;
  customerAmount?: string;
  surveyPrice?: string;
  needsComparison?: boolean;
  suggestedPrice?: string;
  reference?: AnalysisReference;
  referenceCount: number;
  evidenceCount: number;
  comparison?: string;
  note?: string;
  history?: { text: string; time: string }[];
}

export interface AnalysisPresentation {
  projectCode: string;
  catalogName: string;
  period?: string;
  assets?: Record<number, AnalysisAssetPresentation>;
}

export function formatAnalysisNumber(value: string, missing = "—"): string {
  if (!value.trim()) return missing;
  const match = /^([+-]?)(\d*)(?:\.(\d*))?(?:[eE]([+-]?\d+))?$/.exec(value.trim());
  if (!match || !(match[2] || match[3]) || !Number.isFinite(Number(value))) return value;
  if (match[4] && Number(value) === 0) return value;
  const digits = match[2] + (match[3] || "");
  const point = match[2].length + Number(match[4] || 0);
  const integer = (point <= 0 ? "0" : digits.slice(0, point).padEnd(point, "0")).replace(/^0+(?=\d)/, "");
  const fraction = point < 0 ? "0".repeat(-point) + digits : digits.slice(point);
  const decimal = fraction || (value.trim().endsWith(".") ? "" : undefined);
  return (match[1] === "-" ? "-" : "") + integer.replace(/\B(?=(\d{3})+(?!\d))/g, ".") + (decimal !== undefined ? "," + decimal : "");
}

export function parseAnalysisNumberInput(display: string): string | null {
  const text = display.trim();
  if (!text) return "";
  if (!/^(?:\d+|\d{1,3}(?:\.\d{3})+)(?:,\d*)?$/.test(text)) return null;
  const raw = text.replace(/\./g, "").replace(",", ".").replace(/^0+(?=\d)/, "");
  return Number.isFinite(Number(raw)) ? raw : null;
}

export function analysisNumberCaret(display: string, position: number, formatted: string): number {
  const count = display.slice(0, position).replace(/[^\d,]/g, "").length;
  if (!count) return 0;
  let seen = 0;
  for (let index = 0; index < formatted.length; index++) {
    if (/[\d,]/.test(formatted[index]) && ++seen === count) return index + 1;
  }
  return formatted.length;
}

export function analysisAmount(price: string, quantity: string): string {
  if (!price.trim() || !quantity.trim()) return "—";
  const amount = Number(price) * Number(quantity);
  return Number.isFinite(amount) ? formatAnalysisNumber(String(amount)) : "—";
}

export function analysisSourcePrice(source?: ProjectAssetImportStagingRowResponse): string {
  return source?.proposed_raw_price || "—";
}

export function analysisAssetPresentation(line: AnalysisDraft, observed?: AnalysisAssetPresentation): AnalysisAssetPresentation {
  if (observed) return observed;
  return {
    code: "",
    status: line.has_unresolved_blocking_line ? "Còn vướng mắc" : line.human_line_confirmed ? "Đã xác nhận" : "Chưa xác nhận",
    statusTone: line.has_unresolved_blocking_line ? "amber" : line.human_line_confirmed ? "green" : "gray",
    viewed: false,
    manual: true,
    referenceCount: 0,
    evidenceCount: 0,
  };
}
