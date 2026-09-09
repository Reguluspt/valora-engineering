import React, { useEffect, useRef, useState } from "react";
import type { NccSelectionAssetLine, NccSelectionCandidate } from "../../api/nccSelection";
import { t } from "../../i18n";

type DrawerTab = "candidates" | "current" | "history";

const NULL_VALUE = "—";

function formatPrice(value: number | null): string {
  if (value === null) return NULL_VALUE;
  return new Intl.NumberFormat("vi-VN").format(value);
}

function warningLabel(code: string): string {
  if (code === "NCC_BELOW_CURRENT_PRICE") return t("ncc.warning.below");
  if (code === "NCC_DIFFERENCE_OVER_15_PERCENT") return t("ncc.warning.over15");
  return code;
}

function historyRevisionLabel(revision: number): string {
  return t("ncc.drawer.historyRevision").replace("{revision}", String(revision));
}

export interface NccSelectionDrawerProps {
  line: NccSelectionAssetLine;
  confirming: boolean;
  confirmationBlocked?: boolean;
  confirmError: string | null;
  onConfirm: (candidate: NccSelectionCandidate) => void;
  onCandidateChange: () => void;
  onClose: () => void;
}

export function NccSelectionDrawer({
  line,
  confirming,
  confirmationBlocked = false,
  confirmError,
  onConfirm,
  onCandidateChange,
  onClose,
}: NccSelectionDrawerProps) {
  const [tab, setTab] = useState<DrawerTab>("candidates");
  // Never preselect: the user must explicitly choose a candidate before any
  // confirm CTA appears, including for stale/current lines.
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null);
  const asideRef = useRef<HTMLElement | null>(null);
  const closeRef = useRef<HTMLButtonElement | null>(null);

  // Drawer accessibility: focus the close control on open, keep keyboard
  // focus within the drawer while open (dependency-free trap), close on
  // Escape, and restore focus on close when the boundary allows it.
  useEffect(() => {
    if (typeof document === "undefined") return;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        onClose();
        return;
      }
      if (event.key !== "Tab") return;
      const aside = asideRef.current;
      if (!aside || typeof aside.querySelectorAll !== "function") return;
      const focusable = Array.from(
        aside.querySelectorAll<HTMLElement>(
          'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
        )
      );
      if (focusable.length === 0) {
        event.preventDefault();
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement as HTMLElement | null;
      if (event.shiftKey && (active === first || !aside.contains(active))) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", handleKeyDown, true);
    return () => {
      document.removeEventListener("keydown", handleKeyDown, true);
      if (
        previouslyFocused &&
        typeof previouslyFocused.focus === "function" &&
        document.contains(previouslyFocused)
      ) {
        previouslyFocused.focus();
      }
    };
  }, [onClose]);

  const selectedCandidate =
    line.candidates.find((candidate) => candidate.quote_line_id === selectedCandidateId) ??
    null;

  return (
    <aside
      ref={asideRef as React.Ref<HTMLElement>}
      className="ncc-drawer"
      role="dialog"
      aria-modal="true"
      aria-label={t("ncc.drawer.title")}
      data-open="true"
    >
      <div className="ncc-drawer-header">
        <h2>{t("ncc.drawer.title")}</h2>
        <button
          ref={closeRef}
          className="ncc-drawer-close"
          type="button"
          onClick={onClose}
          aria-label={t("ncc.action.close")}
        >
          ×
        </button>
      </div>

      <div className="ncc-drawer-asset-summary">
        <p className="ncc-drawer-kicker">{t("ncc.drawer.assetSummary")}</p>
        <h3>{line.asset_name}</h3>
        <dl>
          <dt>{t("ncc.table.unit")}</dt>
          <dd>{line.unit_name ?? NULL_VALUE}</dd>
          <dt>{t("ncc.table.quantity")}</dt>
          <dd>{line.quantity}</dd>
          <dt>{t("ncc.table.currentPrice")}</dt>
          <dd>{formatPrice(line.appraised_unit_price)}</dd>
        </dl>
      </div>

      <nav className="ncc-drawer-tabs" role="tablist">
        <button
          role="tab"
          aria-selected={tab === "candidates"}
          className={tab === "candidates" ? "is-active" : ""}
          onClick={() => setTab("candidates")}
        >
          {t("ncc.drawer.tab.candidates")}
        </button>
        <button
          role="tab"
          aria-selected={tab === "current"}
          className={tab === "current" ? "is-active" : ""}
          onClick={() => setTab("current")}
        >
          {t("ncc.drawer.tab.current")}
        </button>
        <button
          role="tab"
          aria-selected={tab === "history"}
          className={tab === "history" ? "is-active" : ""}
          onClick={() => setTab("history")}
        >
          {t("ncc.drawer.tab.history")}
        </button>
      </nav>

      <div className="ncc-drawer-body">
        {tab === "candidates" && (
          <NccCandidatesTab
            candidates={line.candidates}
            selectedCandidateId={selectedCandidateId}
            onSelect={(candidateId) => {
              setSelectedCandidateId(candidateId);
              onCandidateChange();
            }}
          />
        )}
        {tab === "current" && <NccCurrentTab line={line} />}
        {tab === "history" && <NccHistoryTab history={line.history} />}
      </div>

      {tab === "candidates" && selectedCandidate && (
        <div className="ncc-drawer-confirm">
          {selectedCandidate.warnings.length > 0 && (
            <div className="ncc-warning-summary" data-warning="true">
              <strong>{t("ncc.table.warnings")}</strong>
              <ul>
                {selectedCandidate.warnings.map((code) => (
                  <li key={code}>{warningLabel(code)}</li>
                ))}
              </ul>
            </div>
          )}
          {confirmError && (
            <p className="ncc-confirm-error" role="alert">
              {confirmError}
            </p>
          )}
          <button
            className="ncc-primary-action"
            data-primary-action="true"
            disabled={confirming || confirmationBlocked}
            type="button"
            onClick={() => onConfirm(selectedCandidate)}
          >
            {confirming ? t("ncc.confirm.inProgress") : t("ncc.action.confirm")}
          </button>
        </div>
      )}
    </aside>
  );
}

function NccCandidatesTab({
  candidates,
  selectedCandidateId,
  onSelect,
}: {
  candidates: NccSelectionCandidate[];
  selectedCandidateId: string | null;
  onSelect: (id: string) => void;
}) {
  if (candidates.length === 0) {
    return <p className="ncc-drawer-empty">{t("ncc.drawer.noCandidates")}</p>;
  }
  return (
    <ul className="ncc-candidate-list">
      {candidates.map((candidate) => (
        <li key={candidate.quote_line_id}>
          <label className="ncc-candidate" data-candidate-id={candidate.quote_line_id}>
            <input
              type="radio"
              name={`candidate-${candidates.length}`}
              checked={selectedCandidateId === candidate.quote_line_id}
              onChange={() => onSelect(candidate.quote_line_id)}
            />
            <div>
              <strong>{candidate.supplier_name}</strong>
              <span>{formatPrice(candidate.quoted_unit_price)} {candidate.currency}</span>
              <small>
                {t("ncc.table.difference")}: {formatPrice(candidate.difference_amount)} ·{" "}
                {candidate.difference_percent === null ? NULL_VALUE : `${candidate.difference_percent}%`}
              </small>
            </div>
          </label>
        </li>
      ))}
    </ul>
  );
}

function NccCurrentTab({ line }: { line: NccSelectionAssetLine }) {
  const current = line.current_selection;
  const [showEvidence, setShowEvidence] = useState(false);
  if (!current) {
    return <p className="ncc-drawer-empty">{t("ncc.drawer.noCurrent")}</p>;
  }
  const evidenceRegionId = `ncc-evidence-${line.asset_line_id}`;
  return (
    <div className="ncc-current-detail" data-current="true">
      <dl>
        <dt>{t("ncc.table.selectedSupplier")}</dt>
        <dd>{current.supplier_name}</dd>
        <dt>{t("ncc.table.selectedPrice")}</dt>
        <dd>{formatPrice(current.quoted_unit_price)} {current.currency}</dd>
        <dt>{t("ncc.table.difference")}</dt>
        <dd>{formatPrice(current.difference_amount)}</dd>
        <dt>{t("ncc.table.differencePercent")}</dt>
        <dd>{current.difference_percent === null ? NULL_VALUE : `${current.difference_percent}%`}</dd>
        <dt>{t("ncc.drawer.evidence")}</dt>
        <dd>
          <button
            type="button"
            className="ncc-evidence-toggle"
            aria-expanded={showEvidence}
            aria-controls={evidenceRegionId}
            onClick={() => setShowEvidence((visible) => !visible)}
          >
            {t("ncc.drawer.evidenceToggle")}
          </button>
          {showEvidence && (
            <dl id={evidenceRegionId} data-evidence-detail="true">
              <dt>{t("ncc.drawer.evidenceFilename")}</dt>
              <dd data-evidence-filename="true">{current.evidence.filename ?? NULL_VALUE}</dd>
              <dt>{t("ncc.drawer.evidenceFileId")}</dt>
              <dd data-evidence-file-id={current.evidence.evidence_file_id}>
                {current.evidence.evidence_file_id}
              </dd>
              <dt>{t("ncc.drawer.evidenceStatus")}</dt>
              <dd data-evidence-status="true">{current.evidence.status ?? NULL_VALUE}</dd>
            </dl>
          )}
        </dd>
      </dl>
    </div>
  );
}

function NccHistoryTab({ history }: { history: NccSelectionAssetLine["history"] }) {
  if (history.length === 0) {
    return <p className="ncc-drawer-empty">{t("ncc.drawer.noHistory")}</p>;
  }
  return (
    <ul className="ncc-history-list">
      {history.map((item) => (
        <li key={item.selection_revision} data-revision={item.selection_revision}>
          <strong>{historyRevisionLabel(item.selection_revision)}</strong>
          <span>{item.supplier_name}</span>
          <small>{formatPrice(item.quoted_unit_price)} {item.currency}</small>
        </li>
      ))}
    </ul>
  );
}
