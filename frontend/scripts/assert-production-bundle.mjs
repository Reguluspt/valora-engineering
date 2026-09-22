import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const forbiddenMarkers = [
  { kind: "demonstration data", value: "DỮ LIỆU MINH HỌA — KHÔNG PHẢI HỒ SƠ THẬT" },
  { kind: "demonstration data", value: "MINH-HOA-01" },
  { kind: "demonstration data", value: "demo-rq-1" },
  { kind: "legacy route", value: "/workbench/queue" },
  { kind: "legacy route", value: "/workbench/validation" },
  { kind: "legacy Review Queue surface", value: "Theo dõi các nhiệm vụ cần chuyên viên kiểm tra và quyết định." },
  { kind: "legacy Validation Dashboard surface", value: "Kết quả kiểm tra sẽ được hiển thị khi dữ liệu được cung cấp từ hệ thống." }
];

async function listFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const nested = await Promise.all(entries.map((entry) => {
    const path = join(directory, entry.name);
    return entry.isDirectory() ? listFiles(path) : [path];
  }));
  return nested.flat();
}

const files = await listFiles(fileURLToPath(new URL("../dist", import.meta.url)));
const violations = [];

for (const file of files) {
  const contents = await readFile(file, "utf8");
  for (const marker of forbiddenMarkers) {
    if (contents.includes(marker.value)) {
      violations.push(`${file}: ${marker.kind}: ${marker.value}`);
    }
  }
}

if (violations.length > 0) {
  throw new Error(`Production bundle contains forbidden demo or legacy markers:\n${violations.join("\n")}`);
}

console.log("Production bundle is free of demonstration data and legacy surface markers.");
