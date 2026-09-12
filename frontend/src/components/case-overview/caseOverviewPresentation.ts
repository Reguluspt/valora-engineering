import type { CaseStage, CaseStageResult, CaseStateNextAction } from "../../api/caseState";

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
  DOCUMENT_SYNC_REVIEW: "Rà soát đồng bộ tài liệu",
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

const WORKBENCH_ROUTE_KEYS = new Set([
  "preliminary_request_pending",
  "preliminary_analysis_pending",
  "preliminary_ready_pending",
  "official_intake_pending",
]);

export function mappedNextActionPath(
  nextAction: CaseStateNextAction | null,
  workbenchPath: string
): string | null {
  if (!nextAction) return null;
  if (
    nextAction.kind !== "PENDING" ||
    !nextAction.semantic_route_key ||
    !WORKBENCH_ROUTE_KEYS.has(nextAction.semantic_route_key)
  ) {
    return null;
  }
  return workbenchPath;
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
      description: "Projection hiện tại không cung cấp hành động nghiệp vụ tiếp theo.",
    };
  }
  const stageLabel = nextAction.stage ? CASE_STAGE_LABELS[nextAction.stage] : null;
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
