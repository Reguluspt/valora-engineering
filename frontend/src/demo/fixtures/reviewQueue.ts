import { ReviewQueueItem } from "../../components/workbench/review/ReviewQueueTypes";

export const DEMO_REVIEW_QUEUE: ReviewQueueItem[] = [
  {
    id: "demo-rq-1",
    project_code: "MINH-HOA-01",
    project_name: "Hồ sơ minh họa thiết bị chiếu sáng",
    line_no: 12,
    asset_summary: "Đèn đường LED 150W",
    review_type: "identity",
    priority: "high",
    validation_status: "blocking",
    assigned_to: "demo-reviewer",
    status: "open",
    row_version: 1
  },
  {
    id: "demo-rq-2",
    project_code: "MINH-HOA-02",
    project_name: "Hồ sơ minh họa thiết bị điện",
    line_no: 8,
    asset_summary: "Cáp đồng PVC 25 mm²",
    review_type: "appraised_price",
    priority: "normal",
    validation_status: "warning",
    assigned_to: null,
    status: "in_review",
    row_version: 1
  }
];
