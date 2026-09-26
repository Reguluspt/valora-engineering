import React from "react";
import type { NccSelectionAssetLine, NccSelectionState } from "../../api/nccSelection";
import { t } from "../../i18n";

const NULL_VALUE = "—";

function formatPrice(value: number | null): string {
  if (value === null) return NULL_VALUE;
  return new Intl.NumberFormat("vi-VN").format(value);
}

function formatPercent(value: number | null): string {
  if (value === null) return NULL_VALUE;
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toLocaleString("vi-VN", { maximumFractionDigits: 2 })}%`;
}

function warningLabel(code: string): string {
  if (code === "NCC_BELOW_CURRENT_PRICE") return t("ncc.warning.below");
  if (code === "NCC_DIFFERENCE_OVER_15_PERCENT") return t("ncc.warning.over15");
  return code;
}

export const STATE_LABEL: Record<NccSelectionState, string> = {
  unselected: t("ncc.state.unselected"),
  selected: t("ncc.state.selected"),
  stale: t("ncc.state.stale"),
};

export interface NccSelectionTableProps {
  lines: NccSelectionAssetLine[];
  selectedLineId?: string | null;
  onSelectRow: (line: NccSelectionAssetLine) => void;
}

export function NccSelectionTable({ lines, selectedLineId, onSelectRow }: NccSelectionTableProps) {
  return (
    <div className="ncc-table-wrap">
      <table className="ncc-table">
        <thead>
          <tr>
            <th>STT</th>
            <th>{t("ncc.table.asset")}</th>
            <th>{t("ncc.table.unit")}</th>
            <th>{t("ncc.table.quantity")}</th>
            <th>{t("ncc.table.currentPrice")}</th>
            <th>{t("ncc.table.selectedSupplier")}</th>
            <th>{t("ncc.table.selectedPrice")}</th>
            <th>{t("ncc.table.difference")}</th>
            <th>{t("ncc.table.differencePercent")}</th>
            <th>{t("ncc.table.warnings")}</th>
            <th>{t("ncc.table.state")}</th>
          </tr>
        </thead>
        <tbody>
          {lines.map((line, index) => (
            <NccRow
              key={line.asset_line_id}
              line={line}
              index={index}
              isSelected={selectedLineId === line.asset_line_id}
              onSelect={() => onSelectRow(line)}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function NccRow({
  line,
  index,
  isSelected = false,
  onSelect,
}: {
  line: NccSelectionAssetLine;
  index: number;
  isSelected?: boolean;
  onSelect: () => void;
}) {
  const current = line.current_selection;
  const handleKeyDown = (event: React.KeyboardEvent<HTMLTableRowElement>) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelect();
    }
  };
  return (
    <tr
      className={`ncc-table-row ${isSelected ? "ncc-table-row--selected" : ""}`}
      data-asset-line-id={line.asset_line_id}
      tabIndex={0}
      aria-selected={isSelected ? "true" : undefined}
      aria-label={`${t("action.viewDetails")}: ${line.asset_name}`}
      onClick={onSelect}
      onKeyDown={handleKeyDown}
    >
      <td>{index + 1}</td>
      <td className="ncc-cell-strong">{line.asset_name}</td>
      <td>{line.unit_name ?? NULL_VALUE}</td>
      <td>{line.quantity}</td>
      <td>{formatPrice(line.appraised_unit_price)}</td>
      <td>{current?.supplier_name ?? NULL_VALUE}</td>
      <td>{current ? formatPrice(current.quoted_unit_price) : NULL_VALUE}</td>
      <td>{current ? formatPrice(current.difference_amount) : NULL_VALUE}</td>
      <td>{current ? formatPercent(current.difference_percent) : NULL_VALUE}</td>
      <td>
        {line.candidates.some((candidate) => candidate.warnings.length > 0) ? (
          <span className="ncc-warning-dot" data-warning="true">
            {line.candidates
              .flatMap((c) => c.warnings)
              .filter((v, i, arr) => arr.indexOf(v) === i)
              .map(warningLabel)
              .join(", ")}
          </span>
        ) : (
          <span data-warning="false">—</span>
        )}
      </td>
      <td>
        <span className={`ncc-state ncc-state--${line.state}`} data-state={line.state}>
          {STATE_LABEL[line.state]}
        </span>
      </td>
    </tr>
  );
}
