import type { CaseStage, CaseStageResult, CaseStateNextAction } from "../../api/caseState";
import { projectWorkbenchPath, projectPreliminaryAnalysisPath, projectPreliminaryCompletionPath, projectPreliminaryIntakePath } from "../../contracts/valoraV23";

export function isAssetReviewSessionBridge(nextAction: CaseStateNextAction | null): boolean {
  return nextAction?.kind === "UNAVAILABLE" && ["ASSET_REVIEW", "ASSET_WORKBENCH"].includes(nextAction.stage || "") &&
    nextAction.context?.reason_code === "session_required";
}

export const CASE_STAGE_LABELS: Record<CaseStage, string> = {
  PRELIMINARY_REQUEST: "Yêu cầu sơ bộ",
  PRELIMINARY_ANALYSIS: "Phân tích danh mục",
  PRELIMINARY_READY: "Kết quả sơ bộ",
  OFFICIAL_INTAKE: "Tiếp nhận chính thức",
  ASSET_REVIEW: "Rà soát tài sản",
  ASSET_WORKBENCH: "Bàn làm việc tài sản",
  PRICE_EVIDENCE: "Nguồn giá và chứng cứ",
  SUPPLIER_QUOTES: "Báo giá nhà cung cấp",
  SUPPLIER_SELECTION: "Chọn nhà cung cấp",
  APPRAISAL_RESULT: "Kết quả thẩm định",
  DOCUMENT_WORKSPACE: "Không gian tài liệu",
  DOCUMENT_SYNC_REVIEW: "Rà soát thay đổi tài liệu",
  PUBLISHING_PREPARATION: "Chuẩn bị phát hành",
  PUBLISHING_EXCEPTION_REVIEW: "Xử lý ngoại lệ phát hành",
  PUBLISHING_CONFIRMATION: "Xác nhận phát hành",
  PUBLISHED: "Đã phát hành",
};

export const CASE_RESULT_LABELS: Record<CaseStageResult, string> = {
  COMPLETE: "Hoàn tất",
  IN_PROGRESS: "Đang thực hiện",
  INCOMPLETE: "Chưa hoàn tất",
  BLOCKED: "Đang bị chặn",
  STALE: "Cần xem lại",
  NOT_APPLICABLE: "Không áp dụng",
  NOT_AVAILABLE: "Chưa khả dụng",
};

export function mappedNextActionPath(
  nextAction: CaseStateNextAction | null,
  projectRef: string
): string | null {
  if (!nextAction) return null;
  if (nextAction.stage === "PRICE_EVIDENCE" && nextAction.kind === "PENDING" &&
      nextAction.semantic_route_key === "price_evidence_prepare_required" && nextAction.context?.kind === "price_evidence_preparation")
    return projectWorkbenchPath(projectRef);
  if (isAssetReviewSessionBridge(nextAction)) return projectWorkbenchPath(projectRef);
  if (nextAction.stage === "ASSET_WORKBENCH" && nextAction.semantic_route_key === "asset_workbench_prepare_required" &&
    (nextAction.kind === "PENDING" && nextAction.context?.kind === "asset_workbench_preparation" ||
      nextAction.kind === "UNAVAILABLE" && nextAction.context?.kind === "asset_workbench_diagnostic")) return projectWorkbenchPath(projectRef);
  if (nextAction.kind === "BLOCKER" && nextAction.stage === "ASSET_REVIEW" &&
      nextAction.semantic_route_key === "asset_review_line_blocked") return projectWorkbenchPath(projectRef);
  if (nextAction.kind !== "PENDING" || !nextAction.semantic_route_key) return null;
  if (nextAction.stage === "ASSET_REVIEW" && ["asset_review_line_validate_required",
      "asset_review_line_review_required"].includes(nextAction.semantic_route_key)) return projectWorkbenchPath(projectRef);
  if (nextAction.semantic_route_key === "preliminary_request_pending") {
    return projectPreliminaryIntakePath(projectRef);
  }
  if (nextAction.semantic_route_key === "preliminary_analysis_pending") {
    return projectPreliminaryAnalysisPath(projectRef);
  }
  if (nextAction.semantic_route_key === "preliminary_ready_pending" ||
      nextAction.semantic_route_key === "official_intake_pending") {
    return projectPreliminaryCompletionPath(projectRef);
  }
  return null;
}

export function nextActionCopy(nextAction: CaseStateNextAction | null): {
  eyebrow: string;
  title: string;
  description: string;
} {
  if (!nextAction) {
    return {
      eyebrow: "Trạng thái hiện tại",
      title: "Chưa có hành động tiếp theo được phép",
      description: "Hệ thống hiện chưa cung cấp hành động nghiệp vụ tiếp theo.",
    };
  }
  const stageLabel = nextAction.stage ? CASE_STAGE_LABELS[nextAction.stage] : null;
  if (nextAction.stage === "PRICE_EVIDENCE" && nextAction.semantic_route_key === "price_evidence_prepare_required") return {
    eyebrow: "Hành động tiếp theo", title: "Hoàn thiện nguồn giá và chứng cứ",
    description: "Mở Bàn làm việc để kiểm tra nguồn và chứng cứ của tài sản. Việc mở màn hình không đăng ký, chấp nhận hoặc xác nhận chứng cứ.",
  };
  if (nextAction.stage === "ASSET_WORKBENCH" && nextAction.semantic_route_key === "asset_workbench_prepare_required") return {
    eyebrow: "Hành động tiếp theo", title: "Hoàn thiện mô tả và xác nhận danh mục sẵn sàng",
    description: "Mở Bàn làm việc để xem dữ liệu chính thức và điều kiện hiện tại. Việc mở màn hình không xác nhận danh mục.",
  };
  if (isAssetReviewSessionBridge(nextAction)) return {
    eyebrow: "Hành động tiếp theo", title: "Mở Bàn làm việc tài sản",
    description: "Mở không gian làm việc để xác minh phiên và tải lại trạng thái rà soát. Chưa thực hiện kiểm tra hay quyết định.",
  };
  if (nextAction.kind === "BLOCKER") {
    return {
      eyebrow: "Cần xử lý trước",
      title: stageLabel || "Hồ sơ đang bị chặn",
      description: "Có vấn đề bắt buộc cần được xử lý trước khi hồ sơ có thể tiếp tục.",
    };
  }
  if (nextAction.kind === "PENDING") {
    return {
      eyebrow: "Hành động tiếp theo",
      title: stageLabel || "Tiếp tục xử lý hồ sơ",
      description: "Đây là bước bắt buộc gần nhất do trạng thái hồ sơ xác định.",
    };
  }
  if (nextAction.kind === "UNAVAILABLE") {
    return {
      eyebrow: "Chưa thể tiếp tục",
      title: stageLabel || "Bước tiếp theo chưa khả dụng",
      description: "Nguồn dữ liệu xác định bước này chưa sẵn sàng. Hệ thống không suy đoán trạng thái thay thế.",
    };
  }
  return {
    eyebrow: "Trạng thái hiện tại",
    title: "Chưa có hành động tiếp theo được phép",
    description: "Các bước đã có nguồn dữ liệu đều hoàn tất; các bước tiếp theo chưa được hệ thống hỗ trợ.",
  };
}
