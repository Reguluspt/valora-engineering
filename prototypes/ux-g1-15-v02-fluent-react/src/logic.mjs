/**
 * Presentation-only behavior for VALORA UX-G1.15 v02.
 * These functions do not perform appraisal or Knowledge Base business decisions.
 */
export function amount(unitPrice, qty) {
  if (unitPrice === null || unitPrice === undefined || unitPrice === '' || !Number.isFinite(Number(unitPrice))) return null;
  if (!Number.isFinite(Number(qty)) || Number(qty) < 0) return null;
  return Math.round(Number(unitPrice) * Number(qty));
}

export function suggestedPrice(surveyPrice, transportPercent, transportKnown = true) {
  if (surveyPrice === null || surveyPrice === undefined || surveyPrice === '' || !Number.isFinite(Number(surveyPrice))) return null;
  if (!transportKnown || transportPercent === null || transportPercent === undefined || transportPercent === '' || !Number.isFinite(Number(transportPercent))) return null;
  return Math.round(Number(surveyPrice) * (1 + Number(transportPercent) / 100));
}

export function nextViewed(assets, previousId) {
  return assets.map(a => a.id === previousId ? { ...a, viewed: true } : a);
}

export function warnings(assets) {
  return {
    unviewed: assets.filter(a => !a.viewed).length,
    missingPrice: assets.filter(a => a.proposed === null || a.proposed === undefined).length,
    missingEvidence: assets.filter(a => a.sources.length === 0 || a.sources.every(s => s.links.length === 0 && s.images.length === 0)).length,
    recheck: assets.filter(a => a.needsRecheck).length,
  };
}

export function previewTotal(assets) {
  return assets.reduce((total, a) => total + (amount(a.proposed, a.qty) ?? 0), 0);
}

export function extractLinks(text) {
  return [...new Set((text.match(/https?:\/\/[^\s<>"']+/g) ?? []).map(x => x.replace(/[),.;]+$/, '')))];
}

export function sourcePriorityEligible(asset) {
  // Prototype fixture gate: business matching/ranking is intentionally NOT simulated by this function.
  return asset.match === 'high' && asset.sources.length > 0;
}

export function classifyIdentityChange(original, current) {
  return original.trim().toLocaleLowerCase('vi') !== current.trim().toLocaleLowerCase('vi');
}
