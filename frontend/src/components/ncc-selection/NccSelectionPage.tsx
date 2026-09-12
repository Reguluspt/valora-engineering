import React, { useMemo, useRef, useState } from "react";
import {
  confirmNccSelection,
  type NccSelectionCandidate,
} from "../../api/nccSelection";
import { projectWorkbenchPath } from "../../contracts/valoraV23";
import { useResolvedProject } from "../workbench/project-context";
import { t } from "../../i18n";
import { NccSelectionKpis } from "./NccSelectionKpis";
import { NccSelectionTable } from "./NccSelectionTable";
import { NccSelectionDrawer } from "./NccSelectionDrawer";
import {
  mapConfirmError,
  newIdempotencyKey,
  useNccSelection,
} from "./useNccSelection";
import "./nccSelection.css";

interface NccSelectionPageProps {
  projectRef: string;
  onNavigate: (path: string) => void;
}

type StatusFilter = "all" | "selected" | "unselected" | "stale" | "eligible";

export function NccSelectionPage({ projectRef, onNavigate }: NccSelectionPageProps) {
  const resolved = useResolvedProject(projectRef);

  if (resolved.state === "loading" || resolved.state === "idle") {
    return <NccSelectionSkeleton />;
  }
  if (resolved.state === "error" || !resolved.projectId) {
    return (
      <NccSelectionPageError
        title={resolved.error?.title || t("ncc.error.page.title")}
        message={resolved.error?.message || t("ncc.error.page.message")}
        nextAction={resolved.error?.nextAction || t("ncc.error.retry")}
        onRetry={resolved.retry}
      />
    );
  }

  return (
    <ResolvedNccSelection
      key={resolved.projectId}
      projectId={resolved.projectId}
      projectName={resolved.displayName || "Hồ sơ"}
      onNavigate={onNavigate}
    />
  );
}

function ResolvedNccSelection({
  projectId,
  projectName,
  onNavigate,
}: {
  projectId: string;
  projectName: string;
  onNavigate: (path: string) => void;
}) {
  const selectionState = useNccSelection(projectId);
  const { aggregate, state, error, retry } = selectionState;

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [selectedLineId, setSelectedLineId] = useState<string | null>(null);
  const [confirmingLineId, setConfirmingLineId] = useState<string | null>(null);
  const [confirmError, setConfirmError] = useState<string | null>(null);
  const [conflict, setConflict] = useState<{ lineId: string; message: string } | null>(null);
  const [lastConfirmed, setLastConfirmed] = useState<string | null>(null);
  const idempotencyAttemptRef = useRef<{ fingerprint: string; key: string } | null>(null);
  const confirmInFlightRef = useRef(false);

  const lines = aggregate?.asset_lines ?? [];
  const normalizedSearch = search.trim().toLowerCase();
  const filteredLines = useMemo(
    () =>
      lines.filter((line) => {
        if (normalizedSearch && !line.asset_name.toLowerCase().includes(normalizedSearch)) {
          return false;
        }
        if (statusFilter === "selected") return line.state === "selected";
        if (statusFilter === "unselected") return line.state === "unselected";
        if (statusFilter === "stale") return line.state === "stale";
        if (statusFilter === "eligible") return line.candidates.length > 0;
        return true;
      }),
    [lines, normalizedSearch, statusFilter]
  );
  const selectedLine = lines.find((line) => line.asset_line_id === selectedLineId) ?? null;
  const hasLines = lines.length > 0;

  if (state === "INITIAL_LOADING") return <NccSelectionSkeleton />;
  if (state === "PAGE_ERROR" || !aggregate) {
    return (
      <NccSelectionPageError
        title={error?.title || t("ncc.error.page.title")}
        message={error?.message || t("ncc.error.page.message")}
        nextAction={error?.nextAction || t("ncc.error.retry")}
        onRetry={retry}
      />
    );
  }

  const finishConfirmed = (lineId: string) => {
    idempotencyAttemptRef.current = null;
    setConfirmingLineId(null);
    setSelectedLineId(null);
    setLastConfirmed(lineId);
    retry();
  };

  const handleConfirm = async (candidate: NccSelectionCandidate) => {
    if (!selectedLine) return;
    if (state !== "READY" || conflict || confirmInFlightRef.current) return;
    const expectedRevision = selectedLine.current_selection?.selection_revision ?? 0;
    const attemptFingerprint = JSON.stringify({
      assetLineId: selectedLine.asset_line_id,
      quoteLineId: candidate.quote_line_id,
      expectedRevision,
      acknowledgedWarningCodes: candidate.warnings,
    });
    if (idempotencyAttemptRef.current?.fingerprint !== attemptFingerprint) {
      idempotencyAttemptRef.current = {
        fingerprint: attemptFingerprint,
        key: newIdempotencyKey(),
      };
    }
    const idempotencyKey = idempotencyAttemptRef.current.key;
    confirmInFlightRef.current = true;
    setConfirmingLineId(selectedLine.asset_line_id);
    setConfirmError(null);
    setConflict(null);

    try {
      await confirmNccSelection(projectId, selectedLine.asset_line_id, {
        quote_line_id: candidate.quote_line_id,
        expected_selection_revision: expectedRevision,
        acknowledged_warning_codes: candidate.warnings,
        idempotency_key: idempotencyKey,
        confirmed: true,
      });
      finishConfirmed(selectedLine.asset_line_id);
    } catch (caught) {
      setConfirmingLineId(null);
      const mapped = mapConfirmError(caught);
      if (mapped.kind === "version_conflict") {
        idempotencyAttemptRef.current = null;
        setConflict({ lineId: selectedLine.asset_line_id, message: mapped.message });
        retry();
      } else {
        setConfirmError(mapped.message);
      }
    } finally {
      confirmInFlightRef.current = false;
    }
  };

  return (
    <main className="ncc-page">
      <header className="ncc-page-header">
        <div>
          <p className="ncc-kicker">{t("ncc.pageTitle")}</p>
          <h1>{projectName}</h1>
          <p className="ncc-subtitle">{t("ncc.pageSubtitle")}</p>
        </div>
        <button className="ncc-back-action" type="button" onClick={() => onNavigate(projectWorkbenchPath(projectId))}>
          {t("action.back")}
        </button>
      </header>

      {conflict && (
        <section className="ncc-banner ncc-banner--conflict" data-state="VERSION_CONFLICT" role="alert">
          <strong>{t("ncc.conflict.title")}</strong>
          <span>{conflict.message}</span>
          <button type="button" onClick={() => { setConflict(null); retry(); }}>{t("ncc.conflict.reload")}</button>
        </section>
      )}

      {lastConfirmed && !conflict && (
        <section className="ncc-banner ncc-banner--success" data-state="PARTIAL_SUCCESS" role="status">
          <span>{t("ncc.confirm.success")}</span>
          <button type="button" onClick={() => setLastConfirmed(null)}>{t("ncc.action.close")}</button>
        </section>
      )}

      <NccSelectionKpis kpis={aggregate.kpis} />

      <div className="ncc-toolbar">
        <input
          className="ncc-search"
          type="search"
          placeholder={t("ncc.search.placeholder")}
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          aria-label={t("ncc.search.placeholder")}
        />
        <select
          className="ncc-status-filter"
          value={statusFilter}
          onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}
          aria-label={t("ncc.filter.all")}
        >
          <option value="all">{t("ncc.filter.all")}</option>
          <option value="selected">{t("ncc.filter.selected")}</option>
          <option value="unselected">{t("ncc.filter.unselected")}</option>
          <option value="stale">{t("ncc.filter.stale")}</option>
          <option value="eligible">{t("ncc.filter.eligible")}</option>
        </select>
      </div>

      {!hasLines && <NccEmptyState kind="firstUse" />}
      {hasLines && filteredLines.length === 0 && (
        <NccEmptyState kind="noResults" onReset={() => { setSearch(""); setStatusFilter("all"); }} />
      )}
      {hasLines && filteredLines.length > 0 && (
        <NccSelectionTable
          lines={filteredLines}
          onSelectRow={(line) => {
            idempotencyAttemptRef.current = null;
            setConfirmError(null);
            setSelectedLineId(line.asset_line_id);
          }}
        />
      )}

      {selectedLine && (
        <NccSelectionDrawer
          key={selectedLine.asset_line_id}
          line={selectedLine}
          confirming={confirmingLineId === selectedLine.asset_line_id}
          confirmationBlocked={Boolean(conflict)}
          confirmError={confirmError}
          onConfirm={handleConfirm}
          onCandidateChange={() => {
            idempotencyAttemptRef.current = null;
            setConfirmError(null);
          }}
          onClose={() => {
            idempotencyAttemptRef.current = null;
            setConfirmError(null);
            setSelectedLineId(null);
          }}
        />
      )}
    </main>
  );
}

function NccEmptyState({
  kind,
  onReset,
}: {
  kind: "firstUse" | "noResults";
  onReset?: () => void;
}) {
  if (kind === "firstUse") {
    return (
      <div className="ncc-empty" data-empty="first-use" data-state="EMPTY_FIRST_USE">
        <h3>{t("ncc.empty.firstUse.title")}</h3>
        <p>{t("ncc.empty.firstUse.desc")}</p>
      </div>
    );
  }
  return (
    <div className="ncc-empty" data-empty="no-results" data-state="EMPTY_NO_RESULTS">
      <h3>{t("ncc.empty.noResults.title")}</h3>
      <p>{t("ncc.empty.noResults.desc")}</p>
      <button type="button" onClick={onReset}>{t("ncc.empty.noResults.action")}</button>
    </div>
  );
}

function NccSelectionSkeleton() {
  return (
    <main className="ncc-page ncc-skeleton" data-state="INITIAL_LOADING" role="status" aria-live="polite" aria-label={t("ncc.pageTitle")}>
      <div className="ncc-skeleton-line ncc-skeleton-line--title" />
      <div className="ncc-skeleton-metrics">
        {Array.from({ length: 5 }, (_, index) => (
          <div key={index} />
        ))}
      </div>
      <div className="ncc-skeleton-body" />
    </main>
  );
}

function NccSelectionPageError({
  title,
  message,
  nextAction,
  dataState = "PAGE_ERROR",
  onRetry,
}: {
  title: string;
  message: string;
  nextAction: string;
  dataState?: "PAGE_ERROR";
  onRetry: () => void;
}) {
  return (
    <main className="ncc-page-error" data-state={dataState}>
      <p>{t("ncc.pageTitle")}</p>
      <h1>{title}</h1>
      <span>{message}</span>
      <small>{nextAction}</small>
      <button type="button" onClick={onRetry}>{t("ncc.error.retry")}</button>
    </main>
  );
}
