import { AssetLineContext } from "./ContextPanelTypes";

export const MOCK_CONTEXT_DATA: Record<string, AssetLineContext> = {
  "uuid-1": {
    project_asset_line_id: "uuid-1",
    knowledge_panel: {
      current_spec: {
        technical_specification_id: "spec-1",
        version_id: "v-1",
        status: "active",
        attribute_values: {
          power: "100W",
          voltage: "220V",
          lifespan: "50,000h"
        }
      },
      suggestions: [
        {
          suggestion_id: "sugg-1",
          source_type: "internal_knowledge",
          confidence_score: 0.95,
          summary: "Matches standard Rạng Đông model specifications",
          attribute_values: {
            power: "100W",
            voltage: "220V",
            ip_rating: "IP66"
          },
          evidence_ids: ["ev-1"],
          warnings: []
        }
      ],
      conflicts: []
    },
    price_evidence_panel: {
      quote_batch: {
        id: "qb-1",
        display_name: "Gia Lai LED Materials Batch",
        status: "active",
        conflict_status: "valid",
        spread_percent: 5.8
      },
      quote_lines: [
        {
          id: "ql-1",
          quote_label: "supplier_1",
          supplier_name: "Hoàng Thiên Hà Co",
          quoted_unit_price: 850000,
          currency_code: "VND",
          evidence_id: "ev-10",
          status: "active"
        },
        {
          id: "ql-2",
          quote_label: "supplier_2",
          supplier_name: "Gia Hưng Phát Distributor",
          quoted_unit_price: 900000,
          currency_code: "VND",
          evidence_id: "ev-11",
          status: "active"
        }
      ],
      appraised_price_decision: {
        id: "apd-1",
        selected_unit_price: 850000,
        rationale: "Lowest quote matches appraised budget bounds.",
        status: "approved"
      }
    },
    lineage: {
      original_source_project: { id: "p-org", project_code: "PRJ-2023-A" },
      direct_source_project: { id: "p-dir", project_code: "PRJ-2024-B" },
      lineage_path: ["p-org", "p-dir", "current-proj"]
    },
    validation_issues: [
      {
        id: "val-1",
        severity: "info",
        category: "technical_spec",
        message: "Spec matches active database templates.",
        is_blocking: false
      }
    ]
  },
  "uuid-2": {
    project_asset_line_id: "uuid-2",
    knowledge_panel: {
      current_spec: {
        technical_specification_id: "spec-2",
        version_id: "v-2",
        status: "active",
        attribute_values: {
          power: "150W",
          voltage: "220V"
        }
      },
      suggestions: [
        {
          suggestion_id: "sugg-2",
          source_type: "historical_knowledge",
          confidence_score: 0.86,
          summary: "Suggested based on Project B specs",
          attribute_values: {
            power: "150W",
            voltage: "220V",
            ip_rating: "IP66"
          },
          evidence_ids: ["ev-2"],
          warnings: ["Variance detected in IP Rating"]
        }
      ],
      conflicts: ["IP Rating spec conflicts with design template rules"]
    },
    price_evidence_panel: {
      quote_batch: {
        id: "qb-2",
        display_name: "HĐ 98 - Gia Lai - Tháng 6/2026",
        status: "active",
        conflict_status: "warning",
        spread_percent: 21.3
      },
      quote_lines: [
        {
          id: "ql-3",
          quote_label: "supplier_1",
          supplier_name: "Hoàng Thiên Hà",
          quoted_unit_price: 1000000,
          currency_code: "VND",
          evidence_id: "ev-12",
          status: "active"
        },
        {
          id: "ql-4",
          quote_label: "supplier_2",
          supplier_name: "Gia Hưng Phát",
          quoted_unit_price: 980000,
          currency_code: "VND",
          evidence_id: "ev-13",
          status: "active"
        },
        {
          id: "ql-5",
          quote_label: "supplier_3",
          supplier_name: "Chung Sơn Materials",
          quoted_unit_price: 1050000,
          currency_code: "VND",
          evidence_id: "ev-14",
          status: "active"
        }
      ],
      appraised_price_decision: {
        id: "apd-2",
        selected_unit_price: 950000,
        rationale: "Selected after comparing three supplier quotes",
        status: "pending_review" as any
      }
    },
    lineage: {
      original_source_project: { id: "p-org", project_code: "PRJ-2023-A" },
      direct_source_project: { id: "p-dir", project_code: "PRJ-2024-B" },
      lineage_path: ["p-org", "p-dir", "current-proj"]
    },
    validation_issues: [
      {
        id: "val-2",
        severity: "warning",
        category: "quote",
        message: "Quote variance exceeds 20%",
        is_blocking: false
      }
    ]
  }
};
