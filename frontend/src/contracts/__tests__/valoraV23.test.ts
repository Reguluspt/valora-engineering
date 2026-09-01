import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import {
  APP_ROUTES,
  CANONICAL_CASE_STAGES,
  CANONICAL_CROSS_PRODUCT_UI_STATES,
  FORBIDDEN_NEW_STANDALONE_ROUTE_FRAGMENTS,
  LEGACY_ROUTE_ALIASES,
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
      return FORBIDDEN_NEW_STANDALONE_ROUTE_FRAGMENTS.some((fragment) =>
        route.includes(fragment)
      );
    });
    expect(unapprovedForbiddenRoutes).toEqual([]);
  });

  it("keeps production route literals centralized in the contract", () => {
    const routeOwners = [
      new URL("../../App.tsx", import.meta.url),
      new URL("../../components/layout/AppShell.tsx", import.meta.url)
    ];
    const forbiddenRawLiterals = [
      ...Object.values(APP_ROUTES),
      ...Object.values(LEGACY_ROUTE_ALIASES)
    ];

    for (const owner of routeOwners) {
      const source = readFileSync(owner, "utf8");
      for (const route of forbiddenRawLiterals) {
        expect(source).not.toContain(`"${route}"`);
      }
    }
  });
});
