import React from "react";
import type { NccSelectionKpis } from "../../api/nccSelection";
import { t } from "../../i18n";

export function NccSelectionKpis({ kpis }: { kpis: NccSelectionKpis }) {
  return (
    <div className="ncc-kpis" aria-label="Tóm tắt lựa chọn NCC">
      <NccKpi label={t("ncc.kpi.totalLines")} value={String(kpis.total_asset_lines)} />
      <NccKpi label={t("ncc.kpi.selected")} value={String(kpis.selected)} tone="success" />
      <NccKpi label={t("ncc.kpi.unselected")} value={String(kpis.unselected)} />
      <NccKpi label={t("ncc.kpi.stale")} value={String(kpis.stale)} tone={kpis.stale > 0 ? "warning" : "neutral"} />
      <NccKpi label={t("ncc.kpi.eligible")} value={String(kpis.eligible_quotes)} />
    </div>
  );
}

function NccKpi({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: string;
  tone?: "neutral" | "success" | "warning";
}) {
  return (
    <div className={`ncc-kpi ncc-kpi--${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
