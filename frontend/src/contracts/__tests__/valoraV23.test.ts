import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import {
  APP_ROUTES,
  CANONICAL_CASE_STAGES,
  CANONICAL_CROSS_PRODUCT_UI_STATES,
  FORBIDDEN_NEW_STANDALONE_ROUTE_FRAGMENTS,
  FORBIDDEN_NEW_STANDALONE_ROUTES,
  LEGACY_ROUTE_RATCHET
} from "../valoraV23";


const EXPECTED_CASE_STAGES = [
  "PRELIMINARY_REQUEST",
  "PRELIMINARY_ANALYSIS",
  "PRELIMINARY_READY",
  "OFFICIAL_INTAKE",
  "ASSET_REVIEW",
  "ASSET_WORKBENCH",
  "PRICE_EVIDENCE",
  "SUPPLIER_QUOTES",
  "SUPPLIER_SELECTION",
  "APPRAISAL_RESULT",
  "DOCUMENT_WORKSPACE",
  "DOCUMENT_SYNC_REVIEW",
  "PUBLISHING_PREPARATION",
  "PUBLISHING_EXCEPTION_REVIEW",
  "PUBLISHING_CONFIRMATION",
  "PUBLISHED"
] as const;

const EXPECTED_UI_STATES = [
  "INITIAL_LOADING",
  "SECTION_LOADING",
  "BACKGROUND_REFRESH",
  "PROCESSING",
  "EMPTY_FIRST_USE",
  "EMPTY_NO_RESULTS",
  "EMPTY_NOT_APPLICABLE",
  "EMPTY_COMPLETED",
  "INLINE_ERROR",
  "SECTION_ERROR",
  "PAGE_ERROR",
  "FATAL_ERROR",
  "STALE_DATA",
  "VERSION_CONFLICT",
  "OFFLINE",
  "RECONNECTING",
  "PARTIAL_SUCCESS"
] as const;

const FRONTEND_SRC_ROOT = fileURLToPath(new URL("../../", import.meta.url));
const RAW_PAGE_ROUTE_LITERAL = /(["'`])\/(?:workbench(?:\/[^"'`\r\n]*)?|queue|validation|kscl|qc|approval|lock-version|nccq(?:-[^"'`\r\n]*)?|rule-check|audit|global-audit|export-pdf|pdf-export)\1/g;

function productionTsxFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) {
      return entry.name === "__tests__" ? [] : productionTsxFiles(path);
    }
    return entry.isFile() && entry.name.endsWith(".tsx") ? [path] : [];
  });
}

describe("VALORA UI/UX v2.3 implementation contract", () => {
  it("keeps the canonical case-stage and cross-product state vocabularies exact", () => {
    expect(CANONICAL_CASE_STAGES).toEqual(EXPECTED_CASE_STAGES);
    expect(new Set(CANONICAL_CASE_STAGES).size).toBe(16);

    expect(CANONICAL_CROSS_PRODUCT_UI_STATES).toEqual(EXPECTED_UI_STATES);
    expect(new Set(CANONICAL_CROSS_PRODUCT_UI_STATES).size).toBe(17);
  });

  it("allows only the two inventoried legacy routes", () => {
    expect(LEGACY_ROUTE_RATCHET).toEqual([
      "/workbench/queue",
      "/workbench/validation"
    ]);

    const registeredRoutes = Object.values(APP_ROUTES);
    const unapprovedForbiddenRoutes = registeredRoutes.filter((route) => {
      if ((LEGACY_ROUTE_RATCHET as readonly string[]).includes(route)) return false;
      if ((FORBIDDEN_NEW_STANDALONE_ROUTES as readonly string[]).includes(route)) return true;
      return FORBIDDEN_NEW_STANDALONE_ROUTE_FRAGMENTS.some((fragment) =>
        route.includes(fragment)
      );
    });
    expect(unapprovedForbiddenRoutes).toEqual([]);
  });

  it("keeps production page-route literals centralized in the contract", () => {
    const violations = productionTsxFiles(FRONTEND_SRC_ROOT).flatMap((path) => {
      const source = readFileSync(path, "utf8");
      return [...source.matchAll(RAW_PAGE_ROUTE_LITERAL)].map(
        (match) => `${path}: ${match[0]}`
      );
    });

    expect(violations).toEqual([]);
  });

  it("distinguishes forbidden intermediate surfaces from valid NCCQ terminology", () => {
    expect(FORBIDDEN_NEW_STANDALONE_ROUTE_FRAGMENTS).not.toContain("/nccq");
    expect(FORBIDDEN_NEW_STANDALONE_ROUTE_FRAGMENTS).toContain("/nccq-intermediate");
    expect(FORBIDDEN_NEW_STANDALONE_ROUTE_FRAGMENTS).toContain("/nccq-aggregate");
    for (const route of FORBIDDEN_NEW_STANDALONE_ROUTES) {
      expect(route).not.toContain("nccq");
    }
  });
});
