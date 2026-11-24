import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";
import { parse } from "postcss";

const SOURCE_ROOT = fileURLToPath(new URL("../../", import.meta.url));
const INDEX_STYLES = join(SOURCE_ROOT, "index.css");
const TOKEN_STYLES = join(SOURCE_ROOT, "styles", "fluent2-tokens.css");
const PRIMITIVE_STYLES = join(SOURCE_ROOT, "styles", "fluent2-primitives.css");

type DebtRule = {
  label: string;
  pattern: RegExp;
  allowedOccurrences: Readonly<Record<string, number>>;
  forbiddenExamples: readonly string[];
};

function sourcePath(path: string): string {
  return relative(SOURCE_ROOT, path).replaceAll("\\", "/");
}

function productionStyleFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) {
      return entry.name === "__tests__" || entry.name === "demo"
        ? []
        : productionStyleFiles(path);
    }

    const isProductionSource = entry.name.endsWith(".css") || entry.name.endsWith(".tsx");
    const isTestSource = /\.(?:test|spec)\.[^.]+$/.test(entry.name);
    return entry.isFile() && isProductionSource && !isTestSource ? [path] : [];
  });
}

function occurrenceMap(rule: DebtRule): Record<string, number> {
  return Object.fromEntries(
    productionStyleFiles(SOURCE_ROOT).flatMap((path) => {
      const source = readFileSync(path, "utf8");
      const pattern = new RegExp(rule.pattern.source, rule.pattern.flags);
      const count = rule.label === "backdrop blur" ? unauthorizedBackdropCount(sourcePath(path), source) : [...source.matchAll(pattern)].length;
      return count > 0 ? [[sourcePath(path), count] as const] : [];
    })
  );
}

function occurrenceCount(rule: DebtRule, source: string): number {
  const pattern = new RegExp(rule.pattern.source, rule.pattern.flags);
  return [...source.matchAll(pattern)].length;
}

const backdropPattern = /["']?(?:(?:-webkit-)?\bbackdrop-?filter|\bWebkitBackdropFilter)["']?\s*:/gi;
const scrimStylesPath = "components/precase/preliminary-analysis-workspace.css";

function unauthorizedBackdropCount(path: string, source: string): number {
  const count = [...source.matchAll(backdropPattern)].length;
  if (path !== scrimStylesPath || count !== 1) return count;
  let approved = 0;
  parse(source).walkDecls("backdrop-filter", declaration => {
    const selector = declaration.parent;
    const media = selector?.parent;
    if (declaration.value === "blur(2px)" && !declaration.important && selector?.type === "rule" && selector.selector === ".analysis-panel-scrim" && media?.type === "atrule" && media.name === "media" && media.params.replace(/\s/g, "") === "(max-width:950px)" && media.parent?.type === "root") approved++;
  });
  return count - approved;
}

const TEMPORARY_DEBT: readonly DebtRule[] = [
  {
    label: "Astryx imports",
    pattern: /@astryxdesign\/[a-z0-9@/_-]+/gi,
    allowedOccurrences: {},
    forbiddenExamples: ['@import "@astryxdesign/core/astryx.css";'],
  },
  {
    label: "neon cyan literals",
    pattern: /(?:#(?:66fcf1|45f3ff)(?:[0-9a-f]{2})?\b|rgba?\(\s*(?:102(?:\s*,\s*|\s+)252(?:\s*,\s*|\s+)241|69(?:\s*,\s*|\s+)243(?:\s*,\s*|\s+)255)\b[^)]*\))/gi,
    allowedOccurrences: {},
    forbiddenExamples: ["#66fcf1", "#45f3ffff", "rgba(102, 252, 241, 0.1)", "rgb(69 243 255 / 8%)"],
  },
  {
    label: "backdrop blur",
    pattern: backdropPattern,
    allowedOccurrences: {},
    forbiddenExamples: ["backdrop-filter: blur(8px)", 'backdropFilter: "blur(8px)"', 'WebkitBackdropFilter: "blur(8px)"'],
  },
  {
    label: "glass compatibility declarations",
    pattern: /--glass-[a-z0-9-]+\s*:/gi,
    allowedOccurrences: {},
    forbiddenExamples: ["--glass-bg: transparent;"],
  },
  {
    label: "glass token consumption",
    pattern: /var\(\s*--glass-[a-z0-9-]+/gi,
    allowedOccurrences: {},
    forbiddenExamples: ["background: var(--glass-bg);"],
  },
  {
    label: "glass product classes",
    pattern: /(?<![-\w])(?:[a-z0-9_]+[-_])*glass[a-z0-9_]*(?:[-_][a-z0-9_]+)*\b/gi,
    allowedOccurrences: {},
    forbiddenExamples: [".glass-panel", ".glassmorphism-card", '<div className="legacy-glass-card glassPanel" />'],
  },
  {
    label: "legacy visual-token declarations",
    pattern: /["']?--(?:bg-primary|bg-secondary|text-primary|text-muted|accent-cyan|accent-blue|border-color|shadow-sm|shadow-md|shadow-lg)["']?\s*:/gi,
    allowedOccurrences: {},
    forbiddenExamples: ["--accent-cyan: red;", 'style={{ "--bg-primary": "#000" }}'],
  },
  {
    label: "legacy dark surface declarations",
    pattern: /["']?--(?!valora-)[a-z0-9-]*(?:bg|background|canvas|surface)[a-z0-9-]*["']?\s*:\s*["']?(?:#[0-3](?:[0-9a-f]{2}|[0-9a-f]{3}|[0-9a-f]{5}|[0-9a-f]{7})\b|rgba?\s*\()/gi,
    allowedOccurrences: {},
    forbiddenExamples: ["--legacy-surface: #111", '"--panel-bg": "rgba(0, 0, 0, 0.8)"'],
  },
];

const REQUIRED_TOKENS = [
  "--valora-color-canvas",
  "--valora-color-surface-primary",
  "--valora-color-surface-secondary",
  "--valora-color-surface-elevated",
  "--valora-color-surface-selected",
  "--valora-color-text-primary",
  "--valora-color-text-secondary",
  "--valora-color-text-disabled",
  "--valora-color-text-inverse",
  "--valora-color-border-subtle",
  "--valora-color-border-default",
  "--valora-color-border-strong",
  "--valora-color-border-focus",
  "--valora-color-brand-background",
  "--valora-color-brand-hover",
  "--valora-color-brand-pressed",
  "--valora-color-brand-selected",
  "--valora-color-status-success-foreground",
  "--valora-color-status-success-background",
  "--valora-color-status-success-border",
  "--valora-color-status-warning-foreground",
  "--valora-color-status-warning-background",
  "--valora-color-status-warning-border",
  "--valora-color-status-error-foreground",
  "--valora-color-status-error-background",
  "--valora-color-status-error-border",
  "--valora-color-status-info-foreground",
  "--valora-color-status-info-background",
  "--valora-color-status-info-border",
  "--valora-color-status-neutral-foreground",
  "--valora-color-status-neutral-background",
  "--valora-color-status-neutral-border",
  "--valora-color-interactive-hover",
  "--valora-color-interactive-pressed",
  "--valora-color-interactive-disabled",
  "--valora-focus-ring",
  "--valora-font-family-base",
  "--valora-font-size-page-title",
  "--valora-font-size-section-heading",
  "--valora-font-size-body",
  "--valora-font-size-body-secondary",
  "--valora-font-size-label",
  "--valora-font-size-data",
  "--valora-font-size-caption",
  "--valora-space-page",
  "--valora-space-section",
  "--valora-control-height",
  "--valora-table-row-height",
  "--valora-radius-control",
  "--valora-radius-surface",
  "--valora-shadow-elevated",
] as const;

const REQUIRED_PRIMITIVES = [
  ".valora-button",
  ".valora-button--primary",
  ".valora-button--secondary",
  ".valora-button--subtle",
  ".valora-button--danger",
  ".valora-field",
  ".valora-select",
  ".valora-search-field",
  ".valora-message",
  ".valora-status",
  ".valora-command-bar",
  ".valora-table",
  ".valora-panel",
  ".valora-state",
  ".valora-loading",
  ".valora-skeleton",
] as const;

describe("Fluent 2 light visual-system foundation", () => {
  it("permits exactly the PO-approved narrow detail scrim declaration", () => {
    const source = readFileSync(join(SOURCE_ROOT, scrimStylesPath), "utf8");
    expect([...source.matchAll(backdropPattern)]).toHaveLength(1);
    expect(unauthorizedBackdropCount(scrimStylesPath, source)).toBe(0);
  });

  it.each([
    [scrimStylesPath, "@media(max-width:950px){.sidebar{backdrop-filter:blur(2px)}}"],
    [scrimStylesPath, "@media(max-width:960px){.analysis-panel-scrim{backdrop-filter:blur(2px)}}"],
    [scrimStylesPath, ".analysis-panel-scrim{backdrop-filter:blur(2px)}"],
    [scrimStylesPath, "@media(max-width:950px){.analysis-panel-scrim{backdrop-filter:blur(3px)}}"],
    [scrimStylesPath, "@media(max-width:950px){.analysis-panel-scrim{backdrop-filter:blur(2px);backdrop-filter:blur(2px)}}"],
    [scrimStylesPath, "@media(max-width:950px){.analysis-panel-scrim{-webkit-backdrop-filter:blur(2px)}}"],
    [scrimStylesPath, "@media(max-width:950px){.analysis-panel-scrim,.sidebar{backdrop-filter:blur(2px)}}"],
    ["components/layout/Other.css", "@media(max-width:950px){.analysis-panel-scrim{backdrop-filter:blur(2px)}}"],
    ["components/layout/Other.tsx", 'const style = { backdropFilter: "blur(2px)" };'],
    ["components/layout/Other.tsx", 'const style = { WebkitBackdropFilter: "blur(2px)" };'],
    ["components/layout/Other.tsx", 'const style = { "backdrop-filter": "blur(2px)" };'],
  ])("rejects unauthorized backdrop declaration in %s: %s", (path, source) => {
    expect(unauthorizedBackdropCount(path, source)).toBeGreaterThan(0);
  });

  it("loads canonical Fluent tokens and primitives without Astryx imports", () => {
    const source = readFileSync(INDEX_STYLES, "utf8");
    const tokens = source.indexOf('@import "./styles/fluent2-tokens.css";');
    const primitives = source.indexOf('@import "./styles/fluent2-primitives.css";');

    expect(tokens).toBeGreaterThanOrEqual(0);
    expect(primitives).toBeGreaterThan(tokens);
    expect(source).not.toMatch(/@astryxdesign\//i);
  });

  it("defines the required semantic token families", () => {
    const source = readFileSync(TOKEN_STYLES, "utf8");
    for (const token of REQUIRED_TOKENS) {
      expect(source, `Missing semantic token ${token}`).toContain(`${token}:`);
    }
    expect(source).toContain('"Segoe UI"');
  });

  it("does not require legacy migration aliases", () => {
    const source = readFileSync(INDEX_STYLES, "utf8");
    expect(source).not.toMatch(/--(?:bg-primary|bg-secondary|text-primary|text-muted|accent-cyan|accent-blue|border-color|shadow-sm|shadow-md|shadow-lg|glass-[a-z0-9-]+)\s*:/i);
  });

  it("provides reusable shared primitive classes and visible keyboard focus", () => {
    const source = readFileSync(PRIMITIVE_STYLES, "utf8");
    for (const primitive of REQUIRED_PRIMITIVES) {
      expect(source, `Missing shared primitive ${primitive}`).toContain(primitive);
    }
    expect(source).toContain(":focus-visible");
    expect(source).not.toContain("backdrop-filter");
  });

  for (const rule of TEMPORARY_DEBT) {
    it(`recognizes representative ${rule.label} syntax`, () => {
      for (const example of rule.forbiddenExamples) {
        expect(occurrenceCount(rule, example), `Missed forbidden syntax: ${example}`).toBeGreaterThan(0);
      }
    });

    it(`keeps ${rule.label} at zero`, () => {
      expect(occurrenceMap(rule)).toEqual(rule.allowedOccurrences);
    });
  }
});
