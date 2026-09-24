import React from "react";

import type { CaseStateIssue, CaseStateResponse } from "../../api/caseState";
import {
  projectWorkbenchPath,
} from "../../contracts/valoraV23";
import { useResolvedProject } from "../workbench/project-context";
import {
  CASE_RESULT_LABELS,
  CASE_STAGE_LABELS,
  mappedNextActionPath,
  nextActionCopy,
} from "./caseOverviewPresentation";
import { useCaseState } from "./useCaseState";
import "./caseOverview.css";

interface CaseOverviewPageProps {
  projectRef: string;
  onNavigate: (path: string) => void;
}

export function CaseOverviewPage({ projectRef, onNavigate }: CaseOverviewPageProps) {
  const resolved = useResolvedProject(projectRef);

  if (resolved.state === "loading" || resolved.state === "idle") {
    return <CaseOverviewSkeleton />;
  }
  if (resolved.state === "error" || !resolved.projectId) {
    return (
      <CaseOverviewError
        title={resolved.error?.title || "Chưa thể mở hồ sơ"}
        message={resolved.error?.message || "Không thể xác định hồ sơ cần hiển thị."}
        nextAction={resolved.error?.nextAction || "Vui lòng thử lại."}
        onRetry={resolved.retry}
      />
    );
  }

  return (
    <ResolvedCaseOverview
      key={resolved.projectId}
      projectId={resolved.projectId}
      projectName={resolved.displayName || "Hồ sơ"}
      onNavigate={onNavigate}
    />
  );
}

function ResolvedCaseOverview({
  projectId,
  projectName,
  onNavigate,
}: {
  projectId: string;
  projectName: string;
  onNavigate: (path: string) => void;
}) {
  const { projection, state, error, retry } = useCaseState(projectId);

  if (state === "INITIAL_LOADING") return <CaseOverviewSkeleton />;
  if (state === "PAGE_ERROR" || !projection) {
    return (
      <CaseOverviewError
        title={error?.title || "Chưa thể tải trạng thái hồ sơ"}
        message={error?.message || "Hệ thống chưa thể tổng hợp trạng thái hồ sơ."}
        nextAction={error?.nextAction || "Vui lòng thử lại."}
        onRetry={retry}
      />
    );
  }

  return (
    <CaseOverviewContent
      projectName={projectName}
      projection={projection}
      workbenchPath={projectWorkbenchPath(projectId)}
      onNavigate={onNavigate}
    />
  );
}

export function CaseOverviewContent({
  projectName,
  projection,
  workbenchPath,
  onNavigate,
}: {
  projectName: string;
  projection: CaseStateResponse;
  workbenchPath: string;
  onNavigate: (path: string) => void;
}) {
  const currentStageLabel = CASE_STAGE_LABELS[projection.current_stage];
  const actionCopy = nextActionCopy(projection.next_action);
  const actionPath = mappedNextActionPath(projection.next_action, workbenchPath);
  const completeCount = projection.stages.filter((stage) => stage.result === "COMPLETE").length;
  const unavailableCount = projection.stages.filter((stage) => stage.result === "NOT_AVAILABLE").length;

  return (
    <main className="case-overview-page">
      <header className="case-overview-header">
        <div>
          <p className="case-overview-kicker">Tổng quan hồ sơ</p>
          <h1>{projectName}</h1>
          <p className="case-overview-subtitle">
            Theo dõi các bước bắt buộc và mở đúng việc cần xử lý tiếp theo.
          </p>
        </div>
      </header>

      <section className="case-overview-summary" aria-label="Trạng thái hồ sơ">
        <div className="case-state-summary">
          <span>Trạng thái hồ sơ</span>
          <strong>{currentStageLabel}</strong>
          <small>{completeCount}/{projection.stages.length} bước đã xác nhận hoàn tất{unavailableCount > 0 ? ` · ${unavailableCount} bước chưa khả dụng` : ""}</small>
        </div>
        <SummaryMetric label="Vấn đề ngăn bước" value={String(projection.blockers.length)} tone={projection.blockers.length ? "danger" : "neutral"} />
        <SummaryMetric label="Cảnh báo" value={String(projection.warnings.length)} tone={projection.warnings.length ? "warning" : "neutral"} />
        <SummaryMetric label="Cần xem lại" value={String(projection.stale.length)} tone={projection.stale.length ? "stale" : "neutral"} />
      </section>

      <div className="case-overview-layout">
        <div className="case-overview-main-column">
          <section className="case-overview-section" aria-labelledby="case-progress-title">
            <div className="case-overview-section-heading">
              <div>
                <p>Luồng hồ sơ</p>
                <h2 id="case-progress-title">Tiến độ các bước bắt buộc</h2>
              </div>
              <span>{projection.stages.length} bước theo thứ tự hệ thống</span>
            </div>
            <div className="case-stage-list">
              {projection.stages.map((stage, index) => {
                const capability = projection.capabilities.find((item) => item.stage === stage.stage);
                return (
                  <div
                    className={`case-stage-row case-stage-row--${stage.result.toLowerCase().replace(/_/g, "-")}`}
                    data-case-stage={stage.stage}
                    key={stage.stage}
                  >
                    <span className="case-stage-index">{String(index + 1).padStart(2, "0")}</span>
                    <div className="case-stage-copy">
                      <strong>{CASE_STAGE_LABELS[stage.stage]}</strong>
                      {!capability?.available && <small>Chưa có nguồn trạng thái được xác nhận</small>}
                    </div>
                    <span className={`valora-status case-stage-result case-stage-result--${stage.result.toLowerCase().replace(/_/g, "-")}`}>
                      {CASE_RESULT_LABELS[stage.result]}
                    </span>
                  </div>
                );
              })}
            </div>
          </section>

          <div className="case-issue-grid">
            <IssueSection
              kind="blocking"
              title="Vấn đề ngăn bước tiếp theo"
              emptyText="Không có vấn đề bắt buộc đang mở."
              issues={projection.blockers}
            />
            <IssueSection
              kind="warning"
              title="Cảnh báo nổi bật"
              emptyText="Không có cảnh báo đang mở."
              issues={projection.warnings}
            />
            <section className="case-issue-section case-issue-section--stale">
              <div className="case-issue-heading">
                <h2>Dữ liệu cần xem lại</h2>
                <span>{projection.stale.length}</span>
              </div>
              {projection.stale.length === 0 ? (
                <p className="case-issue-empty">Không có dữ liệu hết hiệu lực cần xem lại.</p>
              ) : (
                <ul>
                  {projection.stale.map((item) => (
                    <li data-issue-kind="stale" key={String(item.id ?? item.target_id ?? JSON.stringify(item))}>
                      <strong>Dữ liệu cần xem lại</strong>
                      <span>Hệ thống đã đánh dấu nguồn dữ liệu này cần được xem lại.</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        </div>

        <aside className="case-overview-rail">
          <section className="case-next-action-panel">
            <p>{actionCopy.eyebrow}</p>
            <h2>{actionCopy.title}</h2>
            <span>{actionCopy.description}</span>
            {actionPath && (
              <button
                className="valora-button valora-button--primary case-primary-action"
                data-primary-action={true}
                onClick={() => onNavigate(actionPath)}
                type="button"
              >
                Tiếp tục xử lý
              </button>
            )}
            {!actionPath && (
              <div className="case-next-action-unavailable">
                Chưa có màn xử lý được liên kết cho trạng thái này.
              </div>
            )}
          </section>

          <section className="case-rail-section">
            <p>Ngữ cảnh hồ sơ</p>
            <h3>Chưa được ghi nhận</h3>
            <span>Hệ thống chưa cung cấp vị trí làm việc gần nhất cho hồ sơ này.</span>
          </section>

          <section className="case-rail-section">
            <p>Hoạt động gần đây</p>
            <h3>Chưa được ghi nhận</h3>
            <span>Hệ thống chưa cung cấp hoạt động gần đây của hồ sơ.</span>
          </section>

          <footer className="case-version">
            <span>Phiên bản trạng thái</span>
            <code title={projection.case_version}>{projection.case_version.slice(0, 12)}</code>
          </footer>
        </aside>
      </div>
    </main>
  );
}

function SummaryMetric({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: string;
  tone?: "neutral" | "warning" | "danger" | "stale";
}) {
  return (
    <div className={`case-summary-metric case-summary-metric--${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function IssueSection({
  kind,
  title,
  emptyText,
  issues,
}: {
  kind: "blocking" | "warning";
  title: string;
  emptyText: string;
  issues: CaseStateIssue[];
}) {
  return (
    <section className={`case-issue-section case-issue-section--${kind}`}>
      <div className="case-issue-heading">
        <h2>{title}</h2>
        <span>{issues.length}</span>
      </div>
      {issues.length === 0 ? (
        <p className="case-issue-empty">{emptyText}</p>
      ) : (
        <ul>
          {issues.map((issue) => (
            <li data-issue-kind={kind} key={issue.id}>
              <strong>{kind === "blocking" ? "Cần xử lý bắt buộc" : "Cần chú ý"}</strong>
              <span>Mã tham chiếu {issue.id.slice(0, 8)}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function CaseOverviewSkeleton() {
  return (
    <main className="case-overview-page case-overview-skeleton" role="status" aria-live="polite" aria-label="Đang tải trạng thái hồ sơ">
      <div className="valora-skeleton case-skeleton-line case-skeleton-line--title" />
      <div className="valora-skeleton case-skeleton-line case-skeleton-line--subtitle" />
      <div className="case-skeleton-metrics">
        {Array.from({ length: 4 }, (_, index) => <div className="valora-skeleton" key={index} />)}
      </div>
      <div className="case-skeleton-body">
        <div className="valora-skeleton" />
        <div className="valora-skeleton" />
      </div>
    </main>
  );
}

function CaseOverviewError({
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
    <main className="case-overview-error" data-state={dataState} role="alert">
      <p>Tổng quan hồ sơ</p>
      <h1>{title}</h1>
      <span>{message}</span>
      <small>{nextAction}</small>
      <button className="valora-button valora-button--primary" type="button" onClick={onRetry}>Tải lại trạng thái</button>
    </main>
  );
}
