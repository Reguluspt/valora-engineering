import { draftUrlIssue, sourceEvaluations, sourceHasUrlCredentials, sourceKinds, type SourceDraft } from "./analysisSourceDrafts";

const FORMAT = "valora-source-drafts-v1";
const textFields = ["title", "origin", "currency", "unit", "capturedAt", "specifications", "vat", "delivery", "narrative"] as const;

export function encodeSourceBackup(scope: string, row: number, drafts: SourceDraft[]) {
  if (drafts.some(sourceHasUrlCredentials)) return null;
  return JSON.stringify({
    format: FORMAT, scope, row,
    drafts: drafts.map(({ images, pendingUrls, error, ...draft }) => draft),
  });
}

export function decodeSourceBackup(text: string, scope: string, row: number): SourceDraft[] {
  const backup = JSON.parse(text);
  if (backup?.format !== FORMAT || backup.scope !== scope || backup.row !== row || !Array.isArray(backup.drafts)) {
    throw new Error("Draft backup belongs to another fixture or asset");
  }
  return backup.drafts.map((entry: Record<string, unknown>) => {
    if (!entry || typeof entry.id !== "string" || !/^[\da-f]{8}(?:-[\da-f]{4}){3}-[\da-f]{12}$/i.test(entry.id)
      || typeof entry.createdAt !== "number" || !Number.isFinite(entry.createdAt)
      || typeof entry.kind !== "string" || !Object.prototype.hasOwnProperty.call(sourceKinds, entry.kind)
      || typeof entry.evaluation !== "string" || !Object.prototype.hasOwnProperty.call(sourceEvaluations, entry.evaluation)
      || typeof entry.needsReview !== "boolean"
      || typeof entry.url !== "string" || (entry.url && draftUrlIssue(entry.url))
      || typeof entry.price !== "string" || (entry.price && (!/^\d+(?:\.\d*)?$/.test(entry.price) || !Number.isFinite(Number(entry.price))))
      || textFields.some(field => typeof entry[field] !== "string")) {
      throw new Error("Invalid draft backup");
    }
    const fields = Object.fromEntries(textFields.map(field => [field, entry[field]])) as Pick<SourceDraft, typeof textFields[number]>;
    if (sourceHasUrlCredentials({ url: entry.url, narrative: fields.narrative })) throw new Error("Invalid draft backup");
    return { ...fields, id: entry.id, createdAt: entry.createdAt, url: entry.url, price: entry.price,
      kind: entry.kind as SourceDraft["kind"], evaluation: entry.evaluation as SourceDraft["evaluation"], needsReview: entry.needsReview,
      images: [], pendingUrls: [], error: "" };
  });
}
