const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const ALL_ZERO_HEX = /^0{32}$/;

export function isValidProjectUuid(val: string): boolean {
  if (!UUID_RE.test(val)) return false;
  const hex = val.replace(/-/g, "");
  return !ALL_ZERO_HEX.test(hex);
}
