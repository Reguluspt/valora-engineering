import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const forbiddenMarkers = [
  "DỮ LIỆU MINH HỌA — KHÔNG PHẢI HỒ SƠ THẬT",
  "MINH-HOA-01",
  "demo-rq-1"
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
    if (contents.includes(marker)) {
      violations.push(`${file}: ${marker}`);
    }
  }
}

if (violations.length > 0) {
  throw new Error(`Production bundle contains demonstration data:\n${violations.join("\n")}`);
}

console.log("Production bundle is free of demonstration data markers.");
