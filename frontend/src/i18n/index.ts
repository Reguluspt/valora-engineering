import { vi } from "./vi";
import { TranslationKey } from "./keys";

/**
 * t (Translate)
 * 
 * Simple type-safe Vietnamese-first translation helper function.
 * Merges localized values and falls back safely on keys if missing.
 */
export function t(key: TranslationKey): string {
  return vi[key] ?? key;
}

export { vi };
export type { TranslationKey };
