import { request } from "./client";

export interface PreliminaryRequestManagementItem {
  project_id: string;
  code: string;
  name: string;
  customer_id: string | null;
  current_batch_id: string | null;
  has_retained_batches: boolean;
  current_source_artifact_id: string | null;
  current_source_state: string | null;
}

export interface PreliminaryRequestManagementPage {
  items: PreliminaryRequestManagementItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface PreliminaryBatch {
  id: string;
  project_id: string;
  status: string;
  source_filename: string;
  source_sheet_name: string | null;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  warning_rows: number;
  created_at: string;
  updated_at: string;
}

export interface ImportSourceArtifact {
  id: string;
  import_batch_id: string;
  generation: number;
  original_filename: string;
  detected_format: string;
  content_type: string;
  file_size_bytes: number;
  checksum_sha256: string;
  state: string;
  adapter_name: string | null;
  adapter_version: string | null;
  adapter_metadata: Record<string, unknown>;
  created_by_user_id: string;
  created_at: string;
  available_at: string | null;
}

export interface WorkbookCandidate {
  sheet_name: string;
  header_start_row: number;
  header_end_row: number;
  data_start_row: number;
  candidate_table_bounds: {
    min_row: number;
    max_row: number;
    min_column: number;
    max_column: number;
  };
  header_labels: (string | null)[];
  confidence: number;
  reasons: string[];
  boundary_reason: string;
  boundary_flags: string[];
}

export interface WorkbookStructureSnapshot {
  id: string;
  import_batch_id: string;
  source_artifact_id: string;
  snapshot_version: number;
  source_checksum_sha256: string;
  rule_version: string;
  adapter_name: string;
  adapter_version: string;
  disposition: string;
  candidate_count: number;
  structure_payload: {
    disposition: string;
    disposition_reasons: string[];
    proposed_candidate_index: number | null;
    candidate_count: number;
    candidates: WorkbookCandidate[];
    row_classification?: Record<string, unknown>;
  };
  analysis_digest_sha256: string;
  created_by_user_id: string;
  created_at: string;
}

export type SemanticRole =
  | "row_number" | "raw_asset_name" | "raw_description" | "unit" | "quantity"
  | "customer_unit_price" | "customer_amount" | "reference_value"
  | "appraiser_proposed_price" | "evidence_note" | "ignore";

export interface MappingField {
  source_column_index: number;
  source_column_letter: string;
  original_header: string | null;
  semantic_role: SemanticRole;
}

export interface MappingSnapshot {
  contract_version: string;
  source: { source_artifact_id: string; generation: number; checksum_sha256: string };
  structure: {
    structure_snapshot_id: string;
    snapshot_version: number;
    rule_version: string;
    analysis_digest_sha256: string;
  };
  template_fingerprint_sha256: string;
  candidate: {
    candidate_index: number;
    sheet_name: string;
    header_start_row: number;
    header_end_row: number;
    data_start_row: number;
    min_row: number;
    max_row: number;
    min_column: number;
    max_column: number;
  };
  fields: MappingField[];
}

export interface MappingProposal {
  decision_id: string;
  source_artifact_id: string;
  structure_snapshot_id: string;
  mapping_snapshot: MappingSnapshot;
  mapping_digest_sha256: string;
  review_required: boolean;
  review_reasons: string[];
  exact_profile_id: string | null;
  similar_profile_ids: string[];
  organization_template_id: string | null;
}

export interface MappingDecision {
  decision_id: string;
  proposal_decision_id: string;
  outcome: string;
  mapping_digest_sha256: string;
  memory_scope: "none" | "customer";
  profile_id: string | null;
  source_artifact_id: string;
  structure_snapshot_id: string;
  selection_revision: number | null;
}

export interface MappingMaterialization {
  usage_id: string;
  confirmation_decision_id: string;
  mapping_digest_sha256: string;
  materialized_asset_row_count: number;
  source_artifact_id: string;
  structure_snapshot_id: string;
  selection_revision: number | null;
}

export type MappingRecoveryStatus =
  | "no_selection" | "unresolved_legacy_history" | "selected_unmaterialized"
  | "selected_recovery_required" | "materialized" | "stale_lineage";

export interface MappingRecoveryState {
  project_id: string;
  batch_id: string;
  current_batch_id: string | null;
  current_source_artifact_id: string | null;
  selection_revision: number;
  status: MappingRecoveryStatus;
  official_intake_closed: boolean;
  selected_confirmation_decision_id: string | null;
  selected_structure_snapshot_id: string | null;
  selected_source_artifact_id: string | null;
  selected_candidate: MappingSnapshot["candidate"] | null;
  mapping_snapshot: MappingSnapshot | null;
  mapping_digest_sha256: string | null;
  memory_scope: "none" | "customer" | null;
  profile_id: string | null;
  selected_command_id: string | null;
  selected_outcome: string | null;
  selected_usage_id: string | null;
  current_staging_usage_id: string | null;
  materialized_asset_row_count: number | null;
  materialized_mapping_digest_sha256: string | null;
  recent_proposals: {
    proposal_decision_id: string;
    source_artifact_id: string;
    structure_snapshot_id: string;
    command_id: string;
    terminal_outcomes: { decision_id: string; command_id: string; outcome: string }[];
  }[];
}

const projectPath = (projectId: string) => `/api/v1/projects/${encodeURIComponent(projectId)}`;
const batchPath = (projectId: string, batchId: string) =>
  `${projectPath(projectId)}/asset-imports/${encodeURIComponent(batchId)}`;
const sourcePath = (projectId: string, batchId: string, sourceId: string) =>
  `${batchPath(projectId, batchId)}/source-artifacts/${encodeURIComponent(sourceId)}`;
const mappingPath = (projectId: string, batchId: string) => `${batchPath(projectId, batchId)}/column-mapping`;

export function listPreliminaryRequests(page = 1, pageSize = 25): Promise<PreliminaryRequestManagementPage> {
  return request<PreliminaryRequestManagementPage>(`${projectPath("preliminary-requests")}?page=${page}&page_size=${pageSize}`);
}

export function listPreliminaryBatches(projectId: string): Promise<PreliminaryBatch[]> {
  return request<PreliminaryBatch[]>(`${projectPath(projectId)}/asset-imports`);
}

export function createPreliminaryBatch(projectId: string, sourceFilename: string): Promise<PreliminaryBatch> {
  return request<PreliminaryBatch>(`${projectPath(projectId)}/asset-imports`, {
    method: "POST",
    body: JSON.stringify({ source_filename: sourceFilename, source_sheet_name: null }),
  });
}

export function uploadSourceArtifact(projectId: string, batchId: string, file: File): Promise<ImportSourceArtifact> {
  const body = new FormData();
  body.append("file", file);
  return request<ImportSourceArtifact>(`${batchPath(projectId, batchId)}/source-artifacts`, { method: "POST", body });
}

export function listSourceArtifacts(projectId: string, batchId: string): Promise<ImportSourceArtifact[]> {
  return request<ImportSourceArtifact[]>(`${batchPath(projectId, batchId)}/source-artifacts`);
}

export function getSourceArtifact(projectId: string, batchId: string, sourceId: string): Promise<ImportSourceArtifact> {
  return request<ImportSourceArtifact>(sourcePath(projectId, batchId, sourceId));
}

export function analyzeStructure(projectId: string, batchId: string, sourceId: string): Promise<WorkbookStructureSnapshot> {
  return request<WorkbookStructureSnapshot>(`${sourcePath(projectId, batchId, sourceId)}/structure-snapshots`, { method: "POST" });
}

export function listStructureSnapshots(
  projectId: string, batchId: string, sourceId: string, cursor?: number,
): Promise<WorkbookStructureSnapshot[]> {
  const query = cursor === undefined ? "?limit=50" : `?limit=50&cursor=${cursor}`;
  return request<WorkbookStructureSnapshot[]>(`${sourcePath(projectId, batchId, sourceId)}/structure-snapshots${query}`);
}

export function getStructureSnapshot(
  projectId: string, batchId: string, sourceId: string, snapshotId: string,
): Promise<WorkbookStructureSnapshot> {
  return request<WorkbookStructureSnapshot>(`${sourcePath(projectId, batchId, sourceId)}/structure-snapshots/${encodeURIComponent(snapshotId)}`);
}

export function getMappingRecovery(projectId: string, batchId: string): Promise<MappingRecoveryState> {
  return request<MappingRecoveryState>(`${mappingPath(projectId, batchId)}/state`);
}

export function proposeMapping(
  projectId: string, batchId: string,
  payload: { source_artifact_id: string; structure_snapshot_id: string; candidate_index: number; command_id: string },
): Promise<MappingProposal> {
  return request<MappingProposal>(`${mappingPath(projectId, batchId)}/proposals`, { method: "POST", body: JSON.stringify(payload) });
}

export function confirmMapping(
  projectId: string, batchId: string,
  payload: {
    proposal_decision_id: string;
    mapping_snapshot: MappingSnapshot;
    memory_scope: "none" | "customer";
    supersedes_profile_id: string | null;
    command_id: string;
    expected_selection_revision: number;
  },
): Promise<MappingDecision> {
  return request<MappingDecision>(`${mappingPath(projectId, batchId)}/confirmations`, { method: "POST", body: JSON.stringify(payload) });
}

export function materializeMapping(
  projectId: string, batchId: string,
  payload: { confirmation_decision_id: string; command_id: string; expected_selection_revision: number },
): Promise<MappingMaterialization> {
  return request<MappingMaterialization>(`${mappingPath(projectId, batchId)}/materializations`, { method: "POST", body: JSON.stringify(payload) });
}
