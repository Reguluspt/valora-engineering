export type EvidenceImage = { id: string; name: string; dataUrl: string };
export interface SourceBrief { links: string[]; images: EvidenceImage[] }
export interface AssetBrief { id: string; viewed: boolean; proposed: number | null; qty: number; sources: SourceBrief[]; needsRecheck: boolean; match: 'high' | 'none' | 'similar' | 'manual' }
export function amount(unitPrice: number | null | undefined | string, qty: number): number | null;
export function suggestedPrice(surveyPrice: number | null | undefined | string, transportPercent: number | null | undefined | string, transportKnown?: boolean): number | null;
export function nextViewed<T extends { id: string; viewed: boolean }>(assets: T[], previousId: string): T[];
export function warnings(assets: AssetBrief[]): { unviewed: number; missingPrice: number; missingEvidence: number; recheck: number };
export function previewTotal(assets: AssetBrief[]): number;
export function extractLinks(text: string): string[];
export function sourcePriorityEligible<T extends { match: string; sources: unknown[] }>(asset: T): boolean;
export function classifyIdentityChange(original: string, current: string): boolean;
