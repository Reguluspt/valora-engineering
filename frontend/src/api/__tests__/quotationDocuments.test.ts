import { expect, it, vi } from "vitest";
import { request } from "../client";
import { importQuotationTxt } from "../quotationDocuments";
vi.mock("../client", () => ({ request: vi.fn().mockResolvedValue({}) }));

it("uses multipart and disables auth-refresh mutation replay for both import and recovery", async () => {
  const command = { contract_version: "quotation-txt-import-v1" as const, command_id: crypto.randomUUID(), confirm: true as const,
    expected_case_version: "a".repeat(64), expected_project_row_version: 1, expected_sha256: "b".repeat(64), expected_byte_length: 1 };
  for (const stateVersion of [undefined, 4]) {
    await importQuotationTxt("project", command, new File(["a"], "synthetic.txt"), stateVersion);
    const [path, options, retryDisabled] = vi.mocked(request).mock.calls.at(-1)!;
    expect(retryDisabled).toBe(true); expect(options?.method).toBe("POST");
    const form = options!.body as FormData;
    expect(form.get("file")).toBeInstanceOf(File);
    expect(JSON.parse(form.get("metadata") as string)).toEqual(stateVersion ? { ...command, expected_storage_state_version: 4 } : command);
    expect(path.endsWith(stateVersion ? "/recover" : "/import")).toBe(true);
  }
});
