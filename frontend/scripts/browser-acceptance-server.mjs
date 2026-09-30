import http from "node:http";

const port = 8000;
let authenticated = false;
let classification = "no_change";
let m365Scenario = "normal";
let m365Classification = "no_change";
let documents = [makeDocument("document-1", "Báo cáo hiện trạng")];
let exchangeArtifacts = [
  {
    artifact_id: "working-docx-acceptance",
    connection_id: "connection-acceptance",
    role: "working",
    media: "docx",
    state: "ready",
    display_name: "Báo cáo hiện trạng-working.docx",
    document_id: "document-1",
    document_revision_id: "revision-document-1",
    excel_import_batch_id: null,
    excel_source_artifact_id: null,
  },
  {
    artifact_id: "inbox-xlsx-acceptance",
    connection_id: "connection-acceptance",
    role: "inbox",
    media: "xlsx",
    state: "ready",
    display_name: "Nguồn dữ liệu.xlsx",
    document_id: null,
    document_revision_id: null,
    excel_import_batch_id: "batch-acceptance",
    excel_source_artifact_id: null,
  },
];
let caseScenario = "normal";
let projectScenario = "populated";
let workbenchScenario = "normal";
let workbenchDraftSaved = false;
let nccScenario = "normal";
let precaseScenario = "upload";
let precaseProposalCommandId = null;
let precaseSelectedCommandId = null;
let precaseAnalysis = null;
let precaseAnalysisLostOnce = false;
let nccLines = [];
let nccIdempotencyMap = new Map();

function createNormalNccLines() {
  return [
    {
      asset_line_id: "asset-line-1",
      asset_name: "Máy phay CNC 3 trục",
      unit_id: "unit-1",
      unit_name: "Chiếc",
      quantity: 1,
      appraised_unit_price: 150000000,
      appraised_currency_id: null,
      current_selection: {
        selection_id: "sel-asset-line-1-1",
        selection_revision: 1,
        quote_line_id: "quote-line-101",
        quote_batch_id: "batch-201",
        quote_batch_revision_number: 1,
        supplier_id: "sup-301",
        supplier_name: "Công ty TNHH Cơ khí Tân Phát",
        quoted_unit_price: 145000000,
        currency: "VND",
        quantity: 1,
        unit_of_measure: "Chiếc",
        quote_date: "2026-09-01T08:30:00Z",
        evidence: {
          evidence_file_id: "ev-401",
          filename: "Bao_gia_Tan_Phat_CNC.pdf",
          status: "active",
        },
        current_unit_price: 150000000,
        current_unit_price_currency_id: null,
        difference_amount: -5000000,
        difference_percent: -3.33,
        warnings: ["NCC_BELOW_CURRENT_PRICE"],
        acknowledged_warning_codes: ["NCC_BELOW_CURRENT_PRICE"],
        confirmed_by_user_id: "user-acceptance",
        confirmed_at: "2026-09-02T09:00:00Z",
        stale: false,
      },
      candidates: [
        {
          quote_line_id: "quote-line-101",
          quote_batch_id: "batch-201",
          quote_batch_revision_number: 1,
          supplier_id: "sup-301",
          supplier_name: "Công ty TNHH Cơ khí Tân Phát",
          quoted_unit_price: 145000000,
          currency: "VND",
          quantity: 1,
          unit_of_measure: "Chiếc",
          quote_date: "2026-09-01T08:30:00Z",
          evidence: {
            evidence_file_id: "ev-401",
            filename: "Bao_gia_Tan_Phat_CNC.pdf",
            status: "active",
          },
          difference_amount: -5000000,
          difference_percent: -3.33,
          warnings: ["NCC_BELOW_CURRENT_PRICE"],
          eligible: true,
        },
        {
          quote_line_id: "quote-line-102",
          quote_batch_id: "batch-202",
          quote_batch_revision_number: 1,
          supplier_id: "sup-302",
          supplier_name: "Công ty CP Thiết bị Sao Mai",
          quoted_unit_price: 160000000,
          currency: "VND",
          quantity: 1,
          unit_of_measure: "Chiếc",
          quote_date: "2026-09-02T10:15:00Z",
          evidence: {
            evidence_file_id: "ev-402",
            filename: "Bao_gia_Sao_Mai_CNC.pdf",
            status: "active",
          },
          difference_amount: 10000000,
          difference_percent: 6.67,
          warnings: [],
          eligible: true,
        },
      ],
      history: [
        {
          selection_revision: 1,
          quote_line_id: "quote-line-101",
          supplier_name: "Công ty TNHH Cơ khí Tân Phát",
          quoted_unit_price: 145000000,
          currency: "VND",
          difference_amount: -5000000,
          difference_percent: -3.33,
          warnings: ["NCC_BELOW_CURRENT_PRICE"],
          confirmed_by_user_id: "user-acceptance",
          confirmed_at: "2026-09-02T09:00:00Z",
        },
      ],
      state: "selected",
    },
    {
      asset_line_id: "asset-line-2",
      asset_name: "Máy tiện vạn năng",
      unit_id: "unit-1",
      unit_name: "Chiếc",
      quantity: 2,
      appraised_unit_price: 85000000,
      appraised_currency_id: null,
      current_selection: null,
      candidates: [
        {
          quote_line_id: "quote-line-103",
          quote_batch_id: "batch-203",
          quote_batch_revision_number: 1,
          supplier_id: "sup-303",
          supplier_name: "Công ty TNHH Kỹ thuật Á Châu",
          quoted_unit_price: 98000000,
          currency: "VND",
          quantity: 2,
          unit_of_measure: "Chiếc",
          quote_date: "2026-09-03T14:00:00Z",
          evidence: {
            evidence_file_id: "ev-403",
            filename: "Bao_gia_A_Chau_May_tien.pdf",
            status: "active",
          },
          difference_amount: 13000000,
          difference_percent: 15.29,
          warnings: ["NCC_DIFFERENCE_OVER_15_PERCENT"],
          eligible: true,
        },
        {
          quote_line_id: "quote-line-104",
          quote_batch_id: "batch-204",
          quote_batch_revision_number: 1,
          supplier_id: "sup-304",
          supplier_name: "Công ty CP Cơ điện Hải Đăng",
          quoted_unit_price: 82000000,
          currency: "VND",
          quantity: 2,
          unit_of_measure: "Chiếc",
          quote_date: "2026-09-03T16:20:00Z",
          evidence: {
            evidence_file_id: "ev-404",
            filename: "Bao_gia_Hai_Dang_May_tien.pdf",
            status: "active",
          },
          difference_amount: -3000000,
          difference_percent: -3.53,
          warnings: ["NCC_BELOW_CURRENT_PRICE"],
          eligible: true,
        },
      ],
      history: [],
      state: "unselected",
    },
    {
      asset_line_id: "asset-line-3",
      asset_name: "Máy mài phẳng tự động",
      unit_id: "unit-1",
      unit_name: "Chiếc",
      quantity: 1,
      appraised_unit_price: 65000000,
      appraised_currency_id: null,
      current_selection: {
        selection_id: "sel-asset-line-3-1",
        selection_revision: 1,
        quote_line_id: "quote-line-105",
        quote_batch_id: "batch-205",
        quote_batch_revision_number: 1,
        supplier_id: "sup-305",
        supplier_name: "Công ty TNHH Cơ khí Đại Nam",
        quoted_unit_price: 70000000,
        currency: "VND",
        quantity: 1,
        unit_of_measure: "Chiếc",
        quote_date: "2026-08-28T11:00:00Z",
        evidence: {
          evidence_file_id: "ev-405",
          filename: "Bao_gia_Dai_Nam_cu.pdf",
          status: "active",
        },
        current_unit_price: 65000000,
        current_unit_price_currency_id: null,
        difference_amount: 5000000,
        difference_percent: 7.69,
        warnings: [],
        acknowledged_warning_codes: [],
        confirmed_by_user_id: "user-acceptance",
        confirmed_at: "2026-08-30T10:00:00Z",
        stale: true,
      },
      candidates: [
        {
          quote_line_id: "quote-line-106",
          quote_batch_id: "batch-206",
          quote_batch_revision_number: 2,
          supplier_id: "sup-305",
          supplier_name: "Công ty TNHH Cơ khí Đại Nam",
          quoted_unit_price: 72000000,
          currency: "VND",
          quantity: 1,
          unit_of_measure: "Chiếc",
          quote_date: "2026-09-04T09:00:00Z",
          evidence: {
            evidence_file_id: "ev-406",
            filename: "Bao_gia_Dai_Nam_moi_R2.pdf",
            status: "active",
          },
          difference_amount: 7000000,
          difference_percent: 10.77,
          warnings: [],
          eligible: true,
        },
      ],
      history: [
        {
          selection_revision: 1,
          quote_line_id: "quote-line-105",
          supplier_name: "Công ty TNHH Cơ khí Đại Nam",
          quoted_unit_price: 70000000,
          currency: "VND",
          difference_amount: 5000000,
          difference_percent: 7.69,
          warnings: [],
          confirmed_by_user_id: "user-acceptance",
          confirmed_at: "2026-08-30T10:00:00Z",
        },
      ],
      state: "stale",
    },
    {
      asset_line_id: "asset-line-4",
      asset_name: "Băng tải cấp phôi tự động",
      unit_id: "unit-2",
      unit_name: "Bộ",
      quantity: 1,
      appraised_unit_price: 40000000,
      appraised_currency_id: null,
      current_selection: null,
      candidates: [],
      history: [],
      state: "unselected",
    },
    {
      asset_line_id: "asset-line-5",
      asset_name: "Bộ gá kẹp khí nén chuyên dụng",
      unit_id: "unit-2",
      unit_name: "Bộ",
      quantity: 4,
      appraised_unit_price: null,
      appraised_currency_id: null,
      current_selection: null,
      candidates: [
        {
          quote_line_id: "quote-line-107",
          quote_batch_id: "batch-207",
          quote_batch_revision_number: 1,
          supplier_id: "sup-307",
          supplier_name: "Công ty TNHH Khí nén Vĩnh Thịnh",
          quoted_unit_price: 25000000,
          currency: "VND",
          quantity: 4,
          unit_of_measure: "Bộ",
          quote_date: "2026-09-05T08:00:00Z",
          evidence: {
            evidence_file_id: "ev-407",
            filename: "Bao_gia_Vinh_Thinh.pdf",
            status: "active",
          },
          difference_amount: null,
          difference_percent: null,
          warnings: [],
          eligible: true,
        },
      ],
      history: [],
      state: "unselected",
    },
    {
      asset_line_id: "asset-line-6",
      asset_name: "Hệ thống làm mát tuần hoàn",
      unit_id: "unit-3",
      unit_name: "Hệ thống",
      quantity: 1,
      appraised_unit_price: 0,
      appraised_currency_id: null,
      current_selection: null,
      candidates: [
        {
          quote_line_id: "quote-line-108",
          quote_batch_id: "batch-208",
          quote_batch_revision_number: 1,
          supplier_id: "sup-308",
          supplier_name: "Công ty CP Kỹ thuật Môi trường Xanh",
          quoted_unit_price: 35000000,
          currency: "VND",
          quantity: 1,
          unit_of_measure: "Hệ thống",
          quote_date: "2026-09-05T09:30:00Z",
          evidence: {
            evidence_file_id: "ev-408",
            filename: "Bao_gia_Moi_Truong_Xanh.pdf",
            status: "active",
          },
          difference_amount: 35000000,
          difference_percent: null,
          warnings: [],
          eligible: true,
        },
      ],
      history: [],
      state: "unselected",
    },
  ];
}

function createNoCandidatesNccLines() {
  return [
    {
      asset_line_id: "asset-line-1",
      asset_name: "Máy phay CNC 3 trục",
      unit_id: "unit-1",
      unit_name: "Chiếc",
      quantity: 1,
      appraised_unit_price: 150000000,
      appraised_currency_id: null,
      current_selection: null,
      candidates: [],
      history: [],
      state: "unselected",
    },
    {
      asset_line_id: "asset-line-2",
      asset_name: "Máy tiện vạn năng",
      unit_id: "unit-1",
      unit_name: "Chiếc",
      quantity: 2,
      appraised_unit_price: 85000000,
      appraised_currency_id: null,
      current_selection: null,
      candidates: [],
      history: [],
      state: "unselected",
    },
    {
      asset_line_id: "asset-line-3",
      asset_name: "Máy mài phẳng tự động",
      unit_id: "unit-1",
      unit_name: "Chiếc",
      quantity: 1,
      appraised_unit_price: 65000000,
      appraised_currency_id: null,
      current_selection: null,
      candidates: [],
      history: [],
      state: "unselected",
    },
  ];
}

function resetNccData() {
  nccIdempotencyMap = new Map();
  if (nccScenario === "empty") {
    nccLines = [];
  } else if (nccScenario === "no-candidates") {
    nccLines = createNoCandidatesNccLines();
  } else {
    nccLines = createNormalNccLines();
  }
}

function computeNccKpis(lines) {
  let selected = 0;
  let unselected = 0;
  let stale = 0;
  let eligible_quotes = 0;
  for (const line of lines) {
    if (line.current_selection) {
      selected += 1;
      if (line.current_selection.stale) {
        stale += 1;
      }
    } else {
      unselected += 1;
    }
    eligible_quotes += (line.candidates ? line.candidates.length : 0);
  }
  return {
    total_asset_lines: lines.length,
    selected,
    unselected,
    stale,
    eligible_quotes,
  };
}

function getNccAggregate() {
  return {
    project_id: "project-acceptance",
    kpis: computeNccKpis(nccLines),
    asset_lines: nccLines,
  };
}

resetNccData();

const workbenchProjectId = "a1b2c3d4-1234-4123-8123-123456789abc";
const workbenchLines = Array.from({ length: 18 }, (_, index) => ({
  id: `asset-line-${index + 1}`,
  project_id: workbenchProjectId,
  asset_name: index === 0 ? "Máy cắt kim loại CNC" : `Thiết bị cơ khí ${index + 1}`,
  description: null,
  quantity: index + 1,
  unit_id: null,
  raw_price: null,
  raw_price_currency_id: null,
  appraised_unit_price: 125000000 + index * 1000000,
  appraised_currency_id: null,
  review_status: index % 3 === 0 ? "parsed" : "raw",
  validation_status: index % 4 === 0 ? "needs_review" : "valid",
  brand_id: null,
  manufacturer_id: null,
  version_token: "3",
}));

const caseStages = [
  "PRELIMINARY_REQUEST", "PRELIMINARY_ANALYSIS", "PRELIMINARY_READY",
  "OFFICIAL_INTAKE", "ASSET_REVIEW", "ASSET_WORKBENCH", "PRICE_EVIDENCE",
  "SUPPLIER_QUOTES", "SUPPLIER_SELECTION", "APPRAISAL_RESULT",
  "DOCUMENT_WORKSPACE", "DOCUMENT_SYNC_REVIEW", "PUBLISHING_PREPARATION",
  "PUBLISHING_EXCEPTION_REVIEW", "PUBLISHING_CONFIRMATION", "PUBLISHED",
];

const projectFixture = {
  id: "project-acceptance",
  organization_id: "organization-acceptance",
  customer_id: "customer-acceptance",
  code: "HS-2026-0913",
  name: "Nhà máy Cơ khí An Phú",
  description: "Hồ sơ nghiệm thu browser với provider mô phỏng.",
  status: "draft",
  knowledge_status: "pending",
  fee_amount: 0,
  fee_currency_id: null,
  signer_profile_id: null,
  row_version: 3,
  created_at: "2026-09-13T00:00:00Z",
  updated_at: "2026-09-13T00:00:00Z",
};

const precaseProject = {
  ...projectFixture,
  id: "precase-acceptance",
  code: "SB-2026-010",
  name: "Yêu cầu sơ bộ An Phú",
  customer_id: null,
  current_preliminary_import_batch_id: "batch-precase",
};
const precaseBatch = {
  id: "batch-precase", project_id: "precase-acceptance", status: "created",
  source_filename: "Danh_muc_thiet_bi.xlsx", source_sheet_name: null,
  total_rows: 0, valid_rows: 0, invalid_rows: 0, warning_rows: 0,
  created_at: "2026-09-30T00:00:00Z", updated_at: "2026-09-30T00:00:00Z",
};
const precaseSource = {
  id: "source-precase", import_batch_id: "batch-precase", generation: 1,
  original_filename: "Danh_muc_thiet_bi.xlsx", detected_format: "xlsx",
  content_type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  file_size_bytes: 4096, checksum_sha256: "a".repeat(64), state: "available",
  adapter_name: "xlsx-openpyxl", adapter_version: "1", adapter_metadata: {},
  created_by_user_id: "user-acceptance", created_at: "2026-09-30T00:00:00Z",
  available_at: "2026-09-30T00:00:00Z",
};
const precaseCandidate = {
  sheet_name: "Danh mục", header_start_row: 2, header_end_row: 2, data_start_row: 3,
  candidate_table_bounds: { min_row: 2, max_row: 14, min_column: 1, max_column: 3 },
  header_labels: ["STT", "Tên tài sản", "Số lượng"], confidence: 0.94,
  reasons: ["Vùng bảng có tiêu đề rõ ràng"], boundary_reason: "Kết thúc vùng dữ liệu",
  boundary_flags: [],
};
const precaseSnapshot = {
  id: "structure-precase", import_batch_id: "batch-precase", source_artifact_id: "source-precase",
  snapshot_version: 1, source_checksum_sha256: "a".repeat(64), rule_version: "fixture-v1",
  adapter_name: "xlsx-openpyxl", adapter_version: "1", disposition: "candidate_detected",
  candidate_count: 1, structure_payload: {
    disposition: "candidate_detected", disposition_reasons: [], proposed_candidate_index: 0,
    candidate_count: 1, candidates: [precaseCandidate],
  },
  analysis_digest_sha256: "b".repeat(64), created_by_user_id: "user-acceptance",
  created_at: "2026-09-30T00:00:00Z",
};
const precaseMapping = {
  contract_version: "fixture-v1",
  source: { source_artifact_id: "source-precase", generation: 1, checksum_sha256: "a".repeat(64) },
  structure: { structure_snapshot_id: "structure-precase", snapshot_version: 1,
    rule_version: "fixture-v1", analysis_digest_sha256: "b".repeat(64) },
  template_fingerprint_sha256: "c".repeat(64),
  candidate: { candidate_index: 0, sheet_name: "Danh mục", header_start_row: 2,
    header_end_row: 2, data_start_row: 3, min_row: 2, max_row: 14, min_column: 1, max_column: 3 },
  fields: [
    { source_column_index: 1, source_column_letter: "A", original_header: "STT", semantic_role: "row_number" },
    { source_column_index: 2, source_column_letter: "B", original_header: "Tên tài sản", semantic_role: "raw_asset_name" },
    { source_column_index: 3, source_column_letter: "C", original_header: "Số lượng", semantic_role: "quantity" },
  ],
};

function caseProjection() {
  const blocker = caseScenario === "blocking" ? [{
    id: "issue-blocking-acceptance",
    target_type: "project",
    target_id: projectFixture.id,
    severity: "blocking",
    status: "open",
    row_version: 1,
  }] : [];
  const warning = caseScenario === "warning" ? [{
    id: "issue-warning-acceptance",
    target_type: "project",
    target_id: projectFixture.id,
    severity: "warning",
    status: "open",
    row_version: 1,
  }] : [];
  // Fixture-only projection for UI coverage; PR-01 has no runtime stale provider.
  const stale = caseScenario === "stale" ? [{
    kind: "SOURCE_STALE",
    target_type: "project",
    target_id: projectFixture.id,
  }] : [];
  const prefixComplete = caseScenario === "unavailable";
  return {
    case_version: "a".repeat(64),
    current_stage: prefixComplete ? "OFFICIAL_INTAKE" : "PRELIMINARY_ANALYSIS",
    next_action: caseScenario === "blocking"
      ? { kind: "BLOCKER", stage: "PRELIMINARY_ANALYSIS", semantic_route_key: null, validation_issue_id: blocker[0].id }
      : caseScenario === "unavailable"
        ? { kind: "UNAVAILABLE", stage: "ASSET_REVIEW", semantic_route_key: null, validation_issue_id: null }
        : { kind: "PENDING", stage: "PRELIMINARY_ANALYSIS", semantic_route_key: "preliminary_analysis_pending", validation_issue_id: null },
    stages: caseStages.map((stage, index) => ({
      stage,
      result: index >= 4 ? "NOT_AVAILABLE"
        : prefixComplete || index === 0 ? "COMPLETE"
          : index === 1 && blocker.length ? "BLOCKED" : "INCOMPLETE",
      provider_key: index < 4 ? `${stage.toLowerCase()}_v1` : null,
    })),
    blockers: blocker,
    warnings: warning,
    stale,
    capabilities: caseStages.map((stage, index) => ({
      stage,
      available: index < 4,
      provider_key: index < 4 ? `${stage.toLowerCase()}_v1` : null,
      version: "pr01-prefix-v1",
    })),
  };
}

function precaseCaseProjection() {
  const completed = Boolean(precaseAnalysis);
  const base = caseProjection();
  return {
    ...base,
    case_version: completed ? "c".repeat(64) : "b".repeat(64),
    next_action: completed ? {
      kind: "NO_AUTHORIZED_DOWNSTREAM_ACTION", stage: null,
      semantic_route_key: null, validation_issue_id: null,
    } : {
      kind: "PENDING", stage: "PRELIMINARY_ANALYSIS",
      semantic_route_key: "preliminary_analysis_pending", validation_issue_id: null,
    },
    stages: base.stages.map((stage) => stage.stage === "PRELIMINARY_ANALYSIS"
      ? { ...stage, result: completed ? "COMPLETE" : "INCOMPLETE" } : stage),
    preliminary: {
      project_id: precaseProject.id, customer_id: null,
      project_row_version: completed ? precaseProject.row_version + 1 : precaseProject.row_version,
      current_preliminary_import_batch_id: precaseBatch.id,
      current_source_artifact_id: precaseSource.id,
      current_preliminary_analysis_snapshot_id: completed ? precaseAnalysis.id : null,
      current_preliminary_analysis_version: completed ? precaseAnalysis.version : null,
      current_preliminary_result_artifact_id: null,
      current_preliminary_result_version: null,
      official_intake_commit_id: null,
    },
  };
}

function makeDocument(id, title) {
  return {
    document_id: id,
    title,
    document_type: "valuation_report",
    readiness: {
      document_id: id,
      document_revision_id: `revision-${id}`,
      document_revision: 1,
      binding_id: `binding-${id}`,
      drive_id: "personal-drive-fixture",
      drive_item_id: `item-${id}`,
      file_name: `${title}.docx`,
      file_path: "/drive/root:/Valora",
      web_url: "https://onedrive.live.com/",
      baseline_eligible: true,
      recovery_code: null,
      classification: m365Classification,
      completed_at: "2026-09-13T01:00:00Z",
      affected_region_keys: [],
      is_fresh: m365Classification !== "access_unavailable",
      is_safe_for_freshness_required_action: m365Classification === "no_change",
      stale_reason: null,
      blocking_reason: null,
      next_action: m365Classification === "file_replaced_or_moved" ? "reconnect_or_rebind"
        : m365Classification === "access_unavailable" ? "retry_revalidation"
          : m365Classification === "external_change_in_managed" ? "review_managed_changes" : "check_changes",
      retryable: false,
    },
  };
}

function send(response, status, body, extraHeaders = {}) {
  response.writeHead(status, {
    "Access-Control-Allow-Credentials": "true",
    "Access-Control-Allow-Headers": "Content-Type,X-CSRF-Token",
    "Access-Control-Allow-Methods": "GET,POST,PATCH,OPTIONS",
    "Access-Control-Allow-Origin": "http://localhost:5173",
    "Content-Type": "application/json; charset=utf-8",
    ...extraHeaders,
  });
  response.end(body == null ? "" : JSON.stringify(body));
}

async function readJson(request) {
  const chunks = [];
  for await (const chunk of request) chunks.push(chunk);
  return chunks.length ? JSON.parse(Buffer.concat(chunks).toString("utf8")) : {};
}

const server = http.createServer(async (request, response) => {
  const url = new URL(request.url, `http://localhost:${port}`);
  if (request.method === "OPTIONS") return send(response, 204, null);
  if (url.pathname === "/__fixture/scenario" && request.method === "GET") {
    const nextCase = url.searchParams.get("case");
    const nextProjects = url.searchParams.get("projects");
    const nextWorkbench = url.searchParams.get("workbench");
    const nextNcc = url.searchParams.get("ncc");
    const nextPrecase = url.searchParams.get("precase");
    const nextM365 = url.searchParams.get("m365");
    const nextM365Classification = url.searchParams.get("m365_classification");
    if (nextCase && !["normal", "blocking", "warning", "stale", "unavailable", "loading", "error"].includes(nextCase)) {
      return send(response, 400, { detail: "Unknown case fixture" });
    }
    if (nextProjects && !["populated", "empty", "loading", "error"].includes(nextProjects)) {
      return send(response, 400, { detail: "Unknown project fixture" });
    }
    if (nextWorkbench && !["normal", "loading", "error", "conflict", "locked"].includes(nextWorkbench)) {
      return send(response, 400, { detail: "Unknown workbench fixture" });
    }
    if (nextNcc && !["normal", "empty", "loading", "error", "conflict", "processing", "no-candidates"].includes(nextNcc)) {
      return send(response, 400, { detail: "Unknown ncc fixture" });
    }
    if (nextPrecase && !["upload", "structure", "review", "proposal", "selected", "materialized", "conflict", "stale", "analysis", "analysis-lost"].includes(nextPrecase)) {
      return send(response, 400, { detail: "Unknown Pre-case fixture" });
    }
    if (nextM365 && !["normal", "disconnected", "empty", "error", "denied", "limited", "read-only", "adoption-error", "exchange-error"].includes(nextM365)) {
      return send(response, 400, { detail: "Unknown M365 fixture" });
    }
    if (nextM365Classification && !["no_change", "external_change_outside_managed", "external_change_in_managed", "file_replaced_or_moved", "access_unavailable"].includes(nextM365Classification)) {
      return send(response, 400, { detail: "Unknown M365 classification fixture" });
    }
    if (nextCase) caseScenario = nextCase;
    if (nextProjects) projectScenario = nextProjects;
    if (nextWorkbench) {
      workbenchScenario = nextWorkbench;
      workbenchDraftSaved = false;
    }
    if (nextNcc) {
      nccScenario = nextNcc;
      resetNccData();
    }
    if (nextPrecase) {
      precaseScenario = nextPrecase;
      precaseProposalCommandId = null;
      precaseSelectedCommandId = null;
      precaseAnalysis = null;
      precaseAnalysisLostOnce = false;
    }
    if (nextM365) {
      m365Scenario = nextM365;
      documents = nextM365 === "empty" ? [] : [makeDocument("document-1", "Báo cáo hiện trạng")];
    }
    if (nextM365Classification) m365Classification = nextM365Classification;
    return send(response, 200, {
      case: caseScenario,
      projects: projectScenario,
      workbench: workbenchScenario,
      ncc: nccScenario,
      precase: precaseScenario,
      m365: m365Scenario,
      m365_classification: m365Classification,
    });
  }
  if (url.pathname === "/api/v1/auth/login" && request.method === "POST") {
    const body = await readJson(request);
    if (!body.organization_slug || !body.email || !body.password) {
      return send(response, 422, { detail: { message: "Thiếu thông tin đăng nhập." } });
    }
    authenticated = true;
    return send(response, 200, { status: "ok" }, { "Set-Cookie": "XSRF-TOKEN=fixture-csrf; Path=/" });
  }
  if (url.pathname === "/api/v1/auth/refresh" && request.method === "POST") {
    return send(response, authenticated ? 200 : 401, authenticated ? { status: "ok" } : { detail: "No session" });
  }
  if (url.pathname === "/api/v1/auth/me" && request.method === "GET") {
    if (!authenticated) return send(response, 401, { detail: "No session" });
    return send(response, 200, {
      id: "user-acceptance",
      email: "operator@valora.local",
      full_name: "Nguyễn Minh An",
      organization_id: "organization-acceptance",
      organization_slug: "chi-nhanh-gia-lai",
      status: "active",
      roles: ["operator"],
      permissions: m365Scenario === "limited" ? ["project:read"] : ["project:read", "project:update"],
    });
  }
  if (url.pathname === "/api/v1/auth/logout" && request.method === "POST") {
    authenticated = false;
    return send(response, 204, null);
  }
  if (!authenticated) return send(response, 401, { detail: "No session" });

  if (url.pathname === "/health" && request.method === "GET") {
    return send(response, 200, { status: "healthy" });
  }

  if (url.pathname === "/api/v1/workbench/sessions" && request.method === "POST") {
    if (workbenchScenario === "locked") return send(response, 403, { detail: "Fixture permission denied" });
    return send(response, 200, {
      id: "session-workbench-acceptance",
      user_id: "user-acceptance",
      project_id: workbenchProjectId,
      status: "active",
      row_version: 1,
      created_at: "2026-09-24T00:00:00Z",
      last_active_at: "2026-09-24T00:00:00Z",
      current_selection: null,
    });
  }
  if (url.pathname === "/api/v1/workbench/sessions/session-workbench-acceptance/heartbeat" && request.method === "POST") {
    return send(response, 200, {
      id: "session-workbench-acceptance",
      user_id: "user-acceptance",
      project_id: workbenchProjectId,
      status: "active",
      row_version: 1,
      created_at: "2026-09-24T00:00:00Z",
      last_active_at: "2026-09-24T00:00:00Z",
      current_selection: null,
    });
  }
  if (url.pathname.startsWith("/api/v1/workbench/sessions/session-workbench-acceptance/") && request.method === "POST") {
    return send(response, 200, { status: "ok" });
  }
  if (url.pathname === `/api/v1/projects/${workbenchProjectId}/asset-lines/draft-state` && request.method === "GET") {
    const items = workbenchDraftSaved ? [{
      asset_line_id: "asset-line-1",
      has_saved_draft: true,
      has_unsaved_changes: false,
      is_locked: false,
      is_stale: false,
      draft_status: "saved_draft",
      changed_fields: ["appraised_unit_price"],
      last_saved_at: "2026-09-24T00:00:00Z",
      last_saved_by: "user-acceptance",
    }] : [];
    return send(response, 200, { project_id: workbenchProjectId, items, total: items.length });
  }
  if (url.pathname === `/api/v1/projects/${workbenchProjectId}/asset-lines` && request.method === "GET") {
    if (workbenchScenario === "loading") {
      setTimeout(() => { if (!response.destroyed) send(response, 200, { project_id: workbenchProjectId, items: workbenchLines, total: workbenchLines.length, limit: 50, offset: 0 }); }, 30_000);
      return;
    }
    if (workbenchScenario === "error") return send(response, 503, { detail: "Fixture asset-line read unavailable" });
    return send(response, 200, { project_id: workbenchProjectId, items: workbenchLines, total: workbenchLines.length, limit: 50, offset: 0 });
  }
  if (url.pathname.startsWith(`/api/v1/projects/${workbenchProjectId}/asset-lines/`) && url.pathname.endsWith("/draft") && request.method === "PATCH") {
    if (workbenchScenario === "conflict") return send(response, 409, { detail: "Fixture draft version conflict" });
    const body = await readJson(request);
    workbenchDraftSaved = true;
    return send(response, 200, {
      project_id: workbenchProjectId,
      asset_line_id: "asset-line-1",
      draft_status: "saved_draft",
      field_key: body.field_key,
      has_saved_draft: true,
      has_unsaved_changes: false,
      is_stale: false,
      changed_fields: [body.field_key],
      saved_at: "2026-09-24T00:00:00Z",
    });
  }

  if (url.pathname === "/api/v1/projects" && request.method === "GET") {
    if (projectScenario === "loading") {
      setTimeout(() => { if (!response.destroyed) send(response, 200, [projectFixture]); }, 30_000);
      return;
    }
    if (projectScenario === "error") return send(response, 503, { detail: "Fixture project read unavailable" });
    return send(response, 200, projectScenario === "empty" ? [] : [projectFixture]);
  }
  if (url.pathname === "/api/v1/projects/preliminary-requests" && request.method === "GET") {
    return send(response, 200, {
      items: [{ project_id: precaseProject.id, code: precaseProject.code,
        name: precaseProject.name, customer_id: null, current_batch_id: precaseBatch.id,
        has_retained_batches: true,
        current_source_artifact_id: precaseScenario === "upload" ? null : precaseSource.id,
        current_source_state: precaseScenario === "upload" ? null : "available" }],
      total: 1, page: 1, page_size: 25,
    });
  }
  if (url.pathname === "/api/v1/projects/precase-acceptance" && request.method === "GET") {
    return send(response, 200, precaseProject);
  }
  if (url.pathname === "/api/v1/projects/precase-acceptance/case-state" && request.method === "GET") {
    return send(response, 200, precaseCaseProjection());
  }
  if (url.pathname === "/api/v1/projects/precase-acceptance/preliminary-analyses" && request.method === "POST") {
    const body = await readJson(request);
    if (!precaseAnalysis) {
      if (body.expected_project_version !== precaseProject.row_version ||
          body.import_batch_id !== precaseBatch.id || body.source_artifact_id !== precaseSource.id ||
          body.mapping_profile_usage_id !== "usage-precase" ||
          !body.confirmed || body.line_manifest?.length !== 12 ||
          body.line_manifest.some((line, index) => line.source_row_number !== index + 3 ||
            !line.human_line_confirmed || line.has_unresolved_blocking_line)) {
        return send(response, 409, { detail: "Current analysis authority changed" });
      }
      precaseAnalysis = {
        id: "analysis-precase", project_id: precaseProject.id, version: 1,
        import_batch_id: precaseBatch.id, source_artifact_id: precaseSource.id,
        structure_snapshot_id: precaseSnapshot.id,
        mapping_decision_id: "confirmation-precase",
        mapping_profile_usage_id: "usage-precase",
        mapping_decision_digest_sha256: "d".repeat(64),
        profile_usage_mapping_digest_sha256: "d".repeat(64),
        line_manifest: body.line_manifest,
        line_manifest_digest_sha256: "e".repeat(64),
        finalized_by_user_id: "user-acceptance", finalized_at: "2026-09-30T00:00:00Z",
        idempotency_key: body.idempotency_key,
      };
    } else if (body.idempotency_key !== precaseAnalysis.idempotency_key) {
      return send(response, 409, { detail: "Analysis already finalized" });
    }
    if (precaseScenario === "analysis-lost" && !precaseAnalysisLostOnce) {
      precaseAnalysisLostOnce = true;
      return send(response, 503, { detail: "Response lost after commit" });
    }
    return send(response, 201, { id: precaseAnalysis.id, project_id: precaseProject.id, version: 1 });
  }
  if (url.pathname === "/api/v1/projects/precase-acceptance/preliminary-analyses/analysis-precase" && request.method === "GET") {
    if (!precaseAnalysis) return send(response, 404, { detail: "Analysis absent" });
    const { idempotency_key, ...fact } = precaseAnalysis;
    return send(response, 200, fact);
  }
  const precaseBase = "/api/v1/projects/precase-acceptance/asset-imports";
  const precaseBatchPath = `${precaseBase}/batch-precase`;
  const precaseSourcePath = `${precaseBatchPath}/source-artifacts`;
  const precaseStructurePath = `${precaseSourcePath}/source-precase/structure-snapshots`;
  const precaseMappingPath = `${precaseBatchPath}/column-mapping`;
  if (url.pathname === precaseBase && request.method === "GET") return send(response, 200, [precaseBatch]);
  if (url.pathname === `${precaseBatchPath}/rows` && request.method === "GET") {
    const offset = Number(url.searchParams.get("offset") || 0);
    const limit = Number(url.searchParams.get("limit") || 100);
    const items = Array.from({ length: 12 }, (_, index) => ({
      id: `staging-${index + 3}`, import_batch_id: precaseBatch.id,
      source_row_number: index + 3, validation_status: "valid",
      validation_errors: [], validation_warnings: [],
      proposed_asset_name: `Máy cắt số ${index + 1}`,
      proposed_quantity: index === 0 ? "0" : String(index + 1),
    }));
    return send(response, 200, {
      project_id: precaseProject.id, import_batch_id: precaseBatch.id,
      items: items.slice(offset, offset + limit), total: items.length, offset, limit,
    });
  }
  if (url.pathname === precaseSourcePath && request.method === "GET") {
    return send(response, 200, precaseScenario === "upload" ? [] : [precaseSource]);
  }
  if (url.pathname === precaseSourcePath && request.method === "POST") {
    precaseScenario = "structure";
    return send(response, 201, precaseSource);
  }
  if (url.pathname === `${precaseSourcePath}/source-precase` && request.method === "GET") {
    return send(response, 200, precaseSource);
  }
  if (url.pathname === precaseStructurePath && request.method === "GET") {
    return send(response, 200, ["review", "proposal", "selected", "materialized", "conflict", "stale"].includes(precaseScenario)
      ? [precaseSnapshot] : []);
  }
  if (url.pathname === precaseStructurePath && request.method === "POST") {
    precaseScenario = "review";
    return send(response, 201, precaseSnapshot);
  }
  if (url.pathname === `${precaseMappingPath}/state` && request.method === "GET") {
    const selected = ["selected", "materialized", "analysis", "analysis-lost"].includes(precaseScenario);
    const materialized = ["materialized", "analysis", "analysis-lost"].includes(precaseScenario);
    return send(response, 200, {
      project_id: precaseProject.id, batch_id: precaseBatch.id,
      current_batch_id: precaseBatch.id,
      current_source_artifact_id: precaseScenario === "upload" ? null : precaseSource.id,
      selection_revision: selected ? 8 : 7,
      status: precaseScenario === "stale" ? "stale_lineage"
        : precaseScenario === "selected" ? "selected_unmaterialized"
        : materialized ? "materialized" : "no_selection",
      official_intake_closed: false,
      selected_confirmation_decision_id: selected ? "confirmation-precase" : null,
      selected_structure_snapshot_id: selected ? precaseSnapshot.id : null,
      selected_source_artifact_id: selected ? precaseSource.id : null,
      selected_candidate: selected ? precaseMapping.candidate : null,
      mapping_snapshot: selected ? precaseMapping : null,
      mapping_digest_sha256: selected ? "d".repeat(64) : null,
      memory_scope: selected ? "none" : null, profile_id: null,
      selected_command_id: selected ? (precaseSelectedCommandId || "fixture-confirm") : null,
      selected_outcome: selected ? "accepted" : null,
      selected_usage_id: materialized ? "usage-precase" : null,
      current_staging_usage_id: materialized ? "usage-precase" : null,
      materialized_asset_row_count: materialized ? 12 : null,
      materialized_mapping_digest_sha256: materialized ? "d".repeat(64) : null,
      recent_proposals: precaseProposalCommandId ? [{ proposal_decision_id: "proposal-precase",
        source_artifact_id: precaseSource.id, structure_snapshot_id: precaseSnapshot.id,
        command_id: precaseProposalCommandId, terminal_outcomes: [] }] : [],
    });
  }
  if (url.pathname === `${precaseMappingPath}/proposals` && request.method === "POST") {
    const body = await readJson(request);
    precaseProposalCommandId = body.command_id;
    precaseScenario = "proposal";
    return send(response, 201, {
      decision_id: "proposal-precase", source_artifact_id: precaseSource.id,
      structure_snapshot_id: precaseSnapshot.id, mapping_snapshot: precaseMapping,
      mapping_digest_sha256: "d".repeat(64), review_required: true,
      review_reasons: ["Cần người dùng xác nhận vai trò cột"],
      exact_profile_id: null, similar_profile_ids: [], organization_template_id: null,
    });
  }
  if (url.pathname === `${precaseMappingPath}/confirmations` && request.method === "POST") {
    if (precaseScenario === "conflict") return send(response, 409, { detail: "Phiên bản chọn ánh xạ đã thay đổi." });
    const body = await readJson(request);
    precaseSelectedCommandId = body.command_id;
    precaseScenario = "selected";
    return send(response, 201, { decision_id: "confirmation-precase", selection_revision: 8 });
  }
  if (url.pathname === `${precaseMappingPath}/materializations` && request.method === "POST") {
    precaseScenario = "materialized";
    return send(response, 201, { usage_id: "usage-precase", materialized_asset_row_count: 12,
      confirmation_decision_id: "confirmation-precase", selection_revision: 8 });
  }
  if (url.pathname === "/api/v1/projects/resolve" && request.method === "GET") {
    if (url.searchParams.get("ref") === "precase-acceptance") {
      return send(response, 200, {
        project_id: precaseProject.id,
        display_name: precaseProject.name,
        matched_by: "code",
      });
    }
    if (url.searchParams.get("ref") === "workbench-acceptance") {
      return send(response, 200, {
        project_id: workbenchProjectId,
        display_name: "Hồ sơ nghiệm thu Workbench",
        matched_by: "code",
      });
    }
    return send(response, 200, {
      project_id: "project-acceptance",
      display_name: "Nhà máy Cơ khí An Phú",
      matched_by: "id",
    });
  }
  if (url.pathname === "/api/v1/projects/project-acceptance/case-state" && request.method === "GET") {
    if (caseScenario === "loading") {
      setTimeout(() => { if (!response.destroyed) send(response, 200, caseProjection()); }, 30_000);
      return;
    }
    if (caseScenario === "error") return send(response, 503, { detail: "Fixture case state unavailable" });
    return send(response, 200, caseProjection());
  }

  const nccSelectionsMatch = url.pathname.match(/^\/api\/v1\/projects\/([^/]+)\/ncc-selections$/);
  if (nccSelectionsMatch && request.method === "GET") {
    const projectId = nccSelectionsMatch[1];
    if (projectId !== "project-acceptance") {
      return send(response, 404, { detail: { error_code: "project_not_found", detail: "Không tìm thấy hồ sơ." } });
    }
    if (nccScenario === "loading") {
      setTimeout(() => {
        if (!response.destroyed) send(response, 200, getNccAggregate());
      }, 30_000);
      return;
    }
    if (nccScenario === "error") {
      return send(response, 503, { detail: "Fixture ncc selections unavailable" });
    }
    return send(response, 200, getNccAggregate());
  }

  const nccConfirmMatch = url.pathname.match(/^\/api\/v1\/projects\/([^/]+)\/asset-lines\/([^/]+)\/ncc-selection$/);
  if (nccConfirmMatch && request.method === "POST") {
    const projectId = nccConfirmMatch[1];
    const lineId = nccConfirmMatch[2];
    if (projectId !== "project-acceptance") {
      return send(response, 404, { detail: { error_code: "project_not_found", detail: "Không tìm thấy hồ sơ." } });
    }
    if (nccScenario === "conflict") {
      return send(response, 409, {
        detail: {
          error_code: "selection_revision_conflict",
          detail: "Dữ liệu lựa chọn NCC đã thay đổi. Vui lòng tải lại và xác nhận lại.",
        },
      });
    }

    const body = await readJson(request);
    const {
      quote_line_id,
      expected_selection_revision,
      acknowledged_warning_codes,
      idempotency_key,
      confirmed,
    } = body;

    if (confirmed !== true) {
      return send(response, 400, {
        detail: {
          error_code: "ncc_selection_confirmation_required",
          detail: "Cần xác nhận thao tác.",
        },
      });
    }

    if (!idempotency_key || typeof idempotency_key !== "string" || !idempotency_key.trim() || idempotency_key.length > 128) {
      return send(response, 422, {
        detail: {
          error_code: "invalid_idempotency_key",
          detail: "Khóa idempotency không hợp lệ.",
        },
      });
    }

    if (typeof expected_selection_revision !== "number" || expected_selection_revision < 0) {
      return send(response, 422, {
        detail: {
          error_code: "invalid_expected_selection_revision",
          detail: "Phiên bản lựa chọn không hợp lệ.",
        },
      });
    }

    const requestFingerprint = JSON.stringify({
      lineId,
      quote_line_id,
      expected_selection_revision,
      acknowledged_warning_codes: [...(acknowledged_warning_codes ?? [])].sort(),
    });
    const priorAttempt = nccIdempotencyMap.get(idempotency_key);
    if (priorAttempt) {
      if (priorAttempt.fingerprint !== requestFingerprint) {
        return send(response, 409, { detail: { error_code: "idempotency_key_reused" } });
      }
      return send(response, 200, priorAttempt.selection);
    }

    const targetLine = nccLines.find((line) => line.asset_line_id === lineId);
    if (!targetLine) {
      return send(response, 404, {
        detail: {
          error_code: "project_asset_line_not_found",
          detail: "Không tìm thấy dòng tài sản.",
        },
      });
    }

    const currentRev = targetLine.current_selection ? targetLine.current_selection.selection_revision : 0;
    if (expected_selection_revision !== currentRev) {
      return send(response, 409, {
        detail: {
          error_code: "selection_revision_conflict",
          detail: "Dữ liệu lựa chọn NCC đã thay đổi. Vui lòng tải lại và xác nhận lại.",
        },
      });
    }

    const candidate = targetLine.candidates.find((c) => c.quote_line_id === quote_line_id);
    if (!candidate) {
      return send(response, 404, {
        detail: {
          error_code: "quote_line_not_found",
          detail: "Không tìm thấy dòng báo giá.",
        },
      });
    }

    const executeSuccess = () => {
      const nextRev = currentRev + 1;
      const confirmedAt = new Date().toISOString();
      const currentSelection = {
        selection_id: `sel-${targetLine.asset_line_id}-${nextRev}`,
        selection_revision: nextRev,
        quote_line_id: candidate.quote_line_id,
        quote_batch_id: candidate.quote_batch_id,
        quote_batch_revision_number: candidate.quote_batch_revision_number,
        supplier_id: candidate.supplier_id,
        supplier_name: candidate.supplier_name,
        quoted_unit_price: candidate.quoted_unit_price,
        currency: candidate.currency,
        quantity: candidate.quantity,
        unit_of_measure: candidate.unit_of_measure,
        quote_date: candidate.quote_date,
        evidence: {
          evidence_file_id: candidate.evidence.evidence_file_id,
          filename: candidate.evidence.filename,
          status: candidate.evidence.status,
        },
        current_unit_price: targetLine.appraised_unit_price,
        current_unit_price_currency_id: targetLine.appraised_currency_id,
        difference_amount: candidate.difference_amount,
        difference_percent: candidate.difference_percent,
        warnings: candidate.warnings,
        acknowledged_warning_codes: Array.isArray(acknowledged_warning_codes) ? acknowledged_warning_codes : [],
        confirmed_by_user_id: "user-acceptance",
        confirmed_at: confirmedAt,
        stale: false,
      };

      const historyItem = {
        selection_revision: nextRev,
        quote_line_id: candidate.quote_line_id,
        supplier_name: candidate.supplier_name,
        quoted_unit_price: candidate.quoted_unit_price,
        currency: candidate.currency,
        difference_amount: candidate.difference_amount,
        difference_percent: candidate.difference_percent,
        warnings: candidate.warnings,
        confirmed_by_user_id: "user-acceptance",
        confirmed_at: confirmedAt,
      };

      targetLine.current_selection = currentSelection;
      targetLine.history = [...(targetLine.history || []), historyItem];
      targetLine.state = "selected";

      nccIdempotencyMap.set(idempotency_key, { fingerprint: requestFingerprint, selection: currentSelection });
      return currentSelection;
    };

    if (nccScenario === "processing") {
      setTimeout(() => {
        if (!response.destroyed) {
          const result = executeSuccess();
          send(response, 200, result);
        }
      }, 5000);
      return;
    }

    const result = executeSuccess();
    return send(response, 200, result);
  }
  if (url.pathname === "/api/v1/m365/onedrive/connection" && request.method === "GET") {
    return send(response, 200, {
      connection_id: m365Scenario === "disconnected" ? null : "connection-acceptance",
      drive_id: m365Scenario === "disconnected" ? null : "personal-drive-fixture",
      status: m365Scenario === "disconnected" ? "not_connected" : "active",
      last_verified_at: "2026-09-13T01:00:00Z",
      capability_state: m365Scenario === "disconnected" ? "reconsent-required"
        : m365Scenario === "read-only" ? "read-only" : "exchange-write-ready",
      read_available: m365Scenario !== "disconnected",
      appfolder_write_available: m365Scenario !== "disconnected" && m365Scenario !== "read-only",
    });
  }
  if (url.pathname.endsWith("/adoption-options") && request.method === "GET") {
    if (m365Scenario === "adoption-error") return send(response, 503, { detail: "Fixture adoption options unavailable" });
    const insideFolder = url.searchParams.has("parent_item_id");
    return send(response, 200, {
      project_id: "project-acceptance",
      project_code: "HS-2026-0913",
      project_name: "Nhà máy Cơ khí An Phú",
      connection_id: "connection-acceptance",
      drive_id: "personal-drive-fixture",
      parent_item_id: insideFolder ? "folder-reports" : null,
      data_snapshot: {
        contract_version: "valora-operational-adoption-v1",
        project_id: "project-acceptance",
        project_code: "HS-2026-0913",
        project_name: "Nhà máy Cơ khí An Phú",
        project_row_version: 3,
      },
      templates: [{
        template_version_id: "template-version-acceptance",
        template_name: "Báo cáo thẩm định chuẩn",
        document_type: "valuation_report",
        version_number: 7,
      }],
      items: insideFolder
        ? [{
            drive_item_id: "drive-item-adopt",
            kind: "docx",
            name: "Bao-cao-tham-dinh.docx",
            size_bytes: 184320,
            last_modified_at: "2026-09-13T00:30:00Z",
            web_url: "https://onedrive.live.com/document",
          }]
        : [{
            drive_item_id: "folder-reports",
            kind: "folder",
            name: "Báo cáo 2026",
            size_bytes: null,
            last_modified_at: null,
            web_url: null,
          }],
      truncated: false,
    });
  }
  if (url.pathname.endsWith("/documents") && request.method === "GET") {
    if (m365Scenario === "error") return send(response, 503, { detail: "Fixture document read unavailable" });
    if (m365Scenario === "denied") return send(response, 403, { detail: "Fixture document access denied" });
    documents = documents.map((item) => makeDocument(item.document_id, item.title));
    return send(response, 200, documents);
  }
  if (url.pathname.endsWith("/exchange/artifacts") && request.method === "GET") {
    if (m365Scenario === "exchange-error") return send(response, 503, { detail: "Fixture exchange unavailable" });
    return send(response, 200, exchangeArtifacts);
  }
  if (/\/documents\/[^/]+\/exchange\/(working|export)$/.test(url.pathname) && request.method === "POST") {
    const role = url.pathname.endsWith("/working") ? "working" : "export";
    const body = await readJson(request);
    const artifact = {
      artifact_id: `${role}-copy-${exchangeArtifacts.length}`,
      connection_id: body.connection_id,
      role,
      media: "docx",
      state: "ready",
      display_name: body.destination_name,
      document_id: "document-1",
      document_revision_id: "revision-document-1",
      excel_import_batch_id: null,
      excel_source_artifact_id: null,
    };
    exchangeArtifacts = [...exchangeArtifacts, artifact];
    return send(response, 201, artifact);
  }
  if (url.pathname.endsWith("/exchange/artifacts/inbox-xlsx-acceptance/reimport") && request.method === "POST") {
    return send(response, 200, exchangeArtifacts.find((item) => item.artifact_id === "inbox-xlsx-acceptance"));
  }
  if (url.pathname.endsWith("/documents/provision") && request.method === "POST") {
    const body = await readJson(request);
    if (body.data_snapshot?.contract_version !== "valora-operational-adoption-v1") {
      return send(response, 409, { detail: { error_code: "operational_adoption_snapshot_stale" } });
    }
    const adopted = makeDocument("document-adopted", body.title);
    documents = [...documents, adopted];
    return send(response, 201, {
      document_id: adopted.document_id,
      document_revision_id: adopted.readiness.document_revision_id,
      document_revision: 1,
      binding_id: adopted.readiness.binding_id,
      baseline_id: "baseline-adopted",
      document_type: adopted.document_type,
      title: adopted.title,
      file_name: "Bao-cao-tham-dinh.docx",
      web_url: adopted.readiness.web_url,
    });
  }
  if (url.pathname.endsWith("/revalidation") && request.method === "POST") {
    m365Classification = "external_change_outside_managed";
    return send(response, 200, { classification: m365Classification });
  }
  return send(response, 404, { detail: "Fixture route not found" });
});

server.listen(port, "127.0.0.1", () => {
  process.stdout.write(`Valora browser acceptance API listening on http://localhost:${port}\n`);
});
