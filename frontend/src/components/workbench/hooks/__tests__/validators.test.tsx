import { describe, it, expect } from "vitest";
import { isValidProjectUuid } from "../../validators";

describe("isValidProjectUuid", () => {
  it("accepts valid lowercase UUID", () => {
    expect(isValidProjectUuid("aaaaaaaa-bbbb-4ccc-8ddd-eeee0000ffff")).toBe(true);
  });

  it("accepts valid uppercase UUID", () => {
    expect(isValidProjectUuid("AAAAAAAA-BBBB-4CCC-8DDD-EEEE0000FFFF")).toBe(true);
  });

  it("rejects malformed UUID", () => {
    expect(isValidProjectUuid("not-a-uuid")).toBe(false);
  });

  it("rejects empty input", () => {
    expect(isValidProjectUuid("")).toBe(false);
  });

  it("rejects all-zero UUID", () => {
    expect(isValidProjectUuid("00000000-0000-0000-0000-000000000000")).toBe(false);
  });
});
