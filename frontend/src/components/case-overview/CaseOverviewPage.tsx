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
  const availableCount = projection.capabilities.filter((capability) => capability.available).length;

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
        <div className="case-overview-current-stage" aria-label="Giai đoạn hiện tại" role="group">
          <span>Giai đoạn hiện tại</span>
          <strong>{currentStageLabel}</strong>
          <small>{projection.current_stage}</small>
        </div>
      </header>

      <section className="case-overview-summary" aria-label="Tóm tắt trạng thái">
        <SummaryMetric label="Bước đã hoàn tất" value={`${completeCount}/${projection.stages.length}`} />
        <SummaryMetric label="Nguồn trạng thái sẵn sàng" value={`${availableCount}/${projection.capabilities.length}`} />
        <SummaryMetric label="Vấn đề bắt buộc" value={String(projection.blockers.length)} tone={projection.blockers.length ? "danger" : "neutral"} />
        <SummaryMetric label="Cảnh báo" value={String(projection.warnings.length)} tone={projection.warnings.length ? "warning" : "neutral"} />
        <SummaryMetric label="Cần xem lại" value={String(projection.stale.length)} tone={projection.stale.length ? "warning" : "neutral"} />
      </section>

      <div className="case-overview-layout">
        <div className="case-overview-main-column">
          <section className="case-overview-section" aria-labelledby="case-progress-title">
            <div className="case-overview-section-heading">
              <div>
                <p>Luồng hồ sơ</p>
                <h2 id="case-progress-title">Tiến độ các bước bắt buộc</h2>
              </div>
              <span>16 giai đoạn chuẩn</span>
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
                      <small>{stage.stage}</small>
                    </div>
                    <span className="case-stage-result">{CASE_RESULT_LABELS[stage.result]}</span>
                    <span className="case-stage-capability">
                      {capability?.available ? "Có nguồn dữ liệu" : "Chưa có nguồn dữ liệu"}
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
                      <span>{String(item.target_type ?? "Nguồn trạng thái hồ sơ")}</span>
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
                className="case-primary-action"
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
            <span>Resume Target chưa có nguồn dữ liệu được phê duyệt trong phiên bản này.</span>
          </section>

          <section className="case-rail-section">
            <p>Hoạt động gần đây</p>
            <h3>Chưa được ghi nhận</h3>
            <span>Projection hiện tại chưa cung cấp lịch sử hoạt động của hồ sơ.</span>
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
  tone?: "neutral" | "warning" | "danger";
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
              <span>Mã vấn đề {issue.id.slice(0, 8)} · {issue.target_type}</span>
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
      <div className="case-skeleton-line case-skeleton-line--title" />
      <div className="case-skeleton-line case-skeleton-line--subtitle" />
      <div className="case-skeleton-metrics">
        {Array.from({ length: 4 }, (_, index) => <div key={index} />)}
      </div>
      <div className="case-skeleton-body">
        <div />
        <div />
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
    <main className="case-overview-error" data-state={dataState}>
      <p>Tổng quan hồ sơ</p>
      <h1>{title}</h1>
      <span>{message}</span>
      <small>{nextAction}</small>
      <button type="button" onClick={onRetry}>Tải lại trạng thái</button>
    </main>
  );
}
