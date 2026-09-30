import type { ProjectAssetImportStagingRowResponse } from "../../api/assetImports";
import type { MappingRecoveryState } from "../../api/preliminaryIntake";

export interface AnalysisDraft {
  source_row_number: number;
  quantity: string;
  identity: string;
  accepted_price_basis: string;
  confirmed_reference_price: string;
  transport_percentage: string;
  proposed_unit_price: string;
  human_line_confirmed: boolean;
  has_unresolved_blocking_line: boolean;
}

export interface AnalysisLineManifest {
  identity: string;
  accepted_price_basis: string;
  confirmed_reference_price: number;
  transport_percentage: number;
  proposed_unit_price: number;
  human_line_confirmed: true;
  has_unresolved_blocking_line: false;
  source_row_number: number;
  quantity: number;
}

export function draftFromStaging(row: ProjectAssetImportStagingRowResponse): AnalysisDraft {
  return {
    source_row_number: row.source_row_number,
    quantity: row.proposed_quantity ?? "",
    identity: row.proposed_asset_name ?? "",
    accepted_price_basis: "",
    confirmed_reference_price: "",
    transport_percentage: "",
    proposed_unit_price: "",
    human_line_confirmed: false,
    has_unresolved_blocking_line: false,
  };
}

function finiteNonnegative(value: string): number | null {
  const trimmed = value.trim();
  if (!/^(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(trimmed)) return null;
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
}

export function sourceQuantityValid(value: string): boolean {
  return finiteNonnegative(value) !== null;
}

export function buildAnalysisManifest(drafts: AnalysisDraft[]): AnalysisLineManifest[] | null {
  if (drafts.length === 0) return null;
  const seen = new Set<number>();
  const manifest: AnalysisLineManifest[] = [];
  for (const draft of drafts) {
    const rowNumber = draft.source_row_number;
    if (!Number.isInteger(rowNumber) || rowNumber < 1 || rowNumber > 1_048_576 || seen.has(rowNumber)) return null;
    seen.add(rowNumber);
    const identity = draft.identity.trim();
    const basis = draft.accepted_price_basis.trim();
    const quantity = finiteNonnegative(draft.quantity);
    const referencePrice = finiteNonnegative(draft.confirmed_reference_price);
    const transport = finiteNonnegative(draft.transport_percentage);
    const proposedPrice = finiteNonnegative(draft.proposed_unit_price);
    if (!identity || identity.length > 255 || !basis || basis.length > 64 ||
        quantity === null || referencePrice === null || transport === null || transport > 100 ||
        proposedPrice === null || !draft.human_line_confirmed || draft.has_unresolved_blocking_line) return null;
    manifest.push({
      identity,
      accepted_price_basis: basis,
      confirmed_reference_price: referencePrice,
      transport_percentage: transport,
      proposed_unit_price: proposedPrice,
      human_line_confirmed: true,
      has_unresolved_blocking_line: false,
      source_row_number: rowNumber,
      quantity,
    });
  }
  return manifest;
}

interface PreliminaryAuthority {
  project_id: string;
  current_preliminary_import_batch_id: string | null;
  current_source_artifact_id: string | null;
  current_preliminary_analysis_snapshot_id: string | null;
  official_intake_commit_id: string | null;
}

type MappingAuthority = Pick<MappingRecoveryState,
  "project_id" | "batch_id" | "status" | "current_batch_id" | "current_source_artifact_id" |
  "selected_source_artifact_id" | "selected_structure_snapshot_id" |
  "selected_confirmation_decision_id" | "selected_usage_id" | "current_staging_usage_id" |
  "mapping_digest_sha256" | "materialized_mapping_digest_sha256" | "official_intake_closed">;

export function analysisContextReady(preliminary: PreliminaryAuthority, recovery: MappingAuthority): boolean {
  return Boolean(
    !preliminary.official_intake_commit_id && !preliminary.current_preliminary_analysis_snapshot_id &&
    preliminary.current_preliminary_import_batch_id && preliminary.current_source_artifact_id &&
    recovery.project_id === preliminary.project_id &&
    recovery.batch_id === preliminary.current_preliminary_import_batch_id &&
    recovery.status === "materialized" && !recovery.official_intake_closed &&
    recovery.current_batch_id === preliminary.current_preliminary_import_batch_id &&
    recovery.current_source_artifact_id === preliminary.current_source_artifact_id &&
    recovery.selected_source_artifact_id === preliminary.current_source_artifact_id &&
    recovery.selected_structure_snapshot_id && recovery.selected_confirmation_decision_id &&
    recovery.selected_usage_id && recovery.selected_usage_id === recovery.current_staging_usage_id &&
    recovery.mapping_digest_sha256 && recovery.materialized_mapping_digest_sha256
  );
}
