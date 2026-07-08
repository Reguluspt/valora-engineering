import { ReviewQueueItem } from "./ReviewQueueTypes";

export const MOCK_REVIEW_QUEUE: ReviewQueueItem[] = [
  {
    id: "rq-1",
    project_code: "HĐ-98",
    project_name: "Gia Lai LED Road Build",
    line_no: 12,
    asset_summary: "Đèn đường LED Rạng Đông CSD10 150W",
    review_type: "identity",
    priority: "high",
    validation_status: "blocking",
    assigned_to: "appraiser_1",
    status: "open",
    row_version: 1
  },
  {
    id: "rq-2",
    project_code: "HĐ-98",
    project_name: "Gia Lai LED Road Build",
    line_no: 8,
    asset_summary: "Cáp đồng PVC 25mm2 Cadivi",
    review_type: "appraised_price",
    priority: "normal",
    validation_status: "warning",
    assigned_to: "reviewer_1",
    status: "in_review",
    row_version: 3
  },
  {
    id: "rq-3",
    project_code: "PRJ-2026-X",
    project_name: "Đường dây 110kV Gia Lai",
    line_no: 45,
    asset_summary: "Ống HDPE D50 Sino luồn dây cáp",
    review_type: "taxonomy",
    priority: "low",
    validation_status: "valid",
    assigned_to: null,
    status: "open",
    row_version: 2
  },
  {
    id: "rq-4",
    project_code: "PRJ-2026-Y",
    project_name: "Trạm biến áp Chư Prông",
    line_no: 3,
    asset_summary: "Máy biến áp THIBIDI 3 Pha 250kVA",
    review_type: "qc",
    priority: "high",
    validation_status: "error",
    assigned_to: "reviewer_2",
    status: "in_review",
    row_version: 5
  }
];
