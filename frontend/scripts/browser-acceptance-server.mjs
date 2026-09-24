import http from "node:http";

const port = 8000;
let authenticated = false;
let classification = "no_change";
let documents = [makeDocument("document-1", "Báo cáo hiện trạng")];
let caseScenario = "normal";
let projectScenario = "populated";

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
    stale: [],
    capabilities: caseStages.map((stage, index) => ({
      stage,
      available: index < 4,
      provider_key: index < 4 ? `${stage.toLowerCase()}_v1` : null,
      version: "pr01-prefix-v1",
    })),
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
      classification,
      completed_at: "2026-09-13T01:00:00Z",
      affected_region_keys: [],
      is_fresh: classification !== "access_unavailable",
      is_safe_for_freshness_required_action: classification === "no_change",
      stale_reason: null,
      blocking_reason: null,
      next_action: null,
      retryable: false,
    },
  };
}

function send(response, status, body, extraHeaders = {}) {
  response.writeHead(status, {
    "Access-Control-Allow-Credentials": "true",
    "Access-Control-Allow-Headers": "Content-Type,X-CSRF-Token",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
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
    if (nextCase && !["normal", "blocking", "warning", "unavailable", "loading", "error"].includes(nextCase)) {
      return send(response, 400, { detail: "Unknown case fixture" });
    }
    if (nextProjects && !["populated", "empty", "loading", "error"].includes(nextProjects)) {
      return send(response, 400, { detail: "Unknown project fixture" });
    }
    if (nextCase) caseScenario = nextCase;
    if (nextProjects) projectScenario = nextProjects;
    return send(response, 200, { case: caseScenario, projects: projectScenario });
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
      permissions: ["project:read", "project:update"],
    });
  }
  if (url.pathname === "/api/v1/auth/logout" && request.method === "POST") {
    authenticated = false;
    return send(response, 204, null);
  }
  if (!authenticated) return send(response, 401, { detail: "No session" });

  if (url.pathname === "/api/v1/projects" && request.method === "GET") {
    if (projectScenario === "loading") {
      setTimeout(() => { if (!response.destroyed) send(response, 200, [projectFixture]); }, 30_000);
      return;
    }
    if (projectScenario === "error") return send(response, 503, { detail: "Fixture project read unavailable" });
    return send(response, 200, projectScenario === "empty" ? [] : [projectFixture]);
  }
  if (url.pathname === "/api/v1/projects/resolve" && request.method === "GET") {
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
  if (url.pathname === "/api/v1/m365/onedrive/connection" && request.method === "GET") {
    return send(response, 200, {
      connection_id: "connection-acceptance",
      drive_id: "personal-drive-fixture",
      status: "active",
      last_verified_at: "2026-09-13T01:00:00Z",
    });
  }
  if (url.pathname.endsWith("/adoption-options") && request.method === "GET") {
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
    documents = documents.map((item) => makeDocument(item.document_id, item.title));
    return send(response, 200, documents);
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
    classification = "external_change_outside_managed";
    return send(response, 200, { classification });
  }
  return send(response, 404, { detail: "Fixture route not found" });
});

server.listen(port, "127.0.0.1", () => {
  process.stdout.write(`Valora browser acceptance API listening on http://localhost:${port}\n`);
});
