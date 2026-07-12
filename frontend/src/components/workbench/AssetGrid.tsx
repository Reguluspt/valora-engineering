import React, { useState, useMemo, useRef, UIEvent } from "react";
import { AssetLineGridRow, GridSortState, SortField } from "./AssetGridTypes";
import { AssetGridToolbar } from "./AssetGridToolbar";
import { StatusBadge } from "../common/StatusBadge";
import { InlineDraftCell } from "./drafts/InlineDraftCell";
import { EmptyState } from "../common/EmptyState";

import { InlineEditDraft } from "./drafts/DraftStateTypes";
import { getDraftStatusLabelVi, getDraftStatusBadge } from "./hooks/useWorkbenchDraftState";

interface AssetGridProps {
  rows: AssetLineGridRow[];
  onActiveRowChange?: (id: string | null) => void;
  drafts?: Record<string, InlineEditDraft>;
  onDraftChange?: (id: string, field: string, value: any, baseValue: any, rowVersion: number) => void;
  draftStates?: Record<string, any>;
  onCommitDraft?: (id: string, fields: string[], versionToken: string) => void;
}

export function executeDraftCommit(
  confirm: (message: string) => boolean,
  commit: ((id: string, fields: string[], versionToken: string) => void) | undefined,
  id: string,
  rowVersion: number,
  fields: string[],
  confirmationMessage: string
): boolean {
  if (confirm(confirmationMessage)) {
    if (commit) {
      commit(id, fields, String(rowVersion));
    }
    return true;
  }
  return false;
}

export function AssetGrid({ rows, onActiveRowChange, drafts = {}, onDraftChange, draftStates = {}, onCommitDraft }: AssetGridProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [validationFilter, setValidationFilter] = useState("All");
  const [sortState, setSortState] = useState<GridSortState>({ field: "line_no", order: "asc" });
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [activeId, setActiveId] = useState<string | null>(null);

  // Virtualization Scroll Container Ref
  const [scrollTop, setScrollTop] = useState(0);
  const containerHeight = 400; // Fixed view window height
  const rowHeight = 60; // Expected row height

  // 1. Sort and Filter
  const filteredAndSortedRows = useMemo(() => {
    let result = [...rows];

    // Filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter((r) => r.raw_name.toLowerCase().includes(query));
    }
    if (statusFilter !== "All") {
      result = result.filter((r) => r.review_status === statusFilter);
    }
    if (validationFilter !== "All") {
      result = result.filter((r) => r.validation_status === validationFilter);
    }

    // Sort
    result.sort((a, b) => {
      let valA = a[sortState.field];
      let valB = b[sortState.field];

      if (typeof valA === "string" && typeof valB === "string") {
        return sortState.order === "asc"
          ? valA.localeCompare(valB)
          : valB.localeCompare(valA);
      }
      if (typeof valA === "number" && typeof valB === "number") {
        return sortState.order === "asc" ? valA - valB : valB - valA;
      }
      return 0;
    });

    return result;
  }, [rows, searchQuery, statusFilter, validationFilter, sortState]);

  // 2. Select / Highlight Functions
  const handleRowClick = (id: string) => {
    setActiveId(id);
    if (onActiveRowChange) {
      onActiveRowChange(id);
    }
  };

  const handleCheckboxClick = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    const nextSelected = new Set(selectedIds);
    if (nextSelected.has(id)) {
      nextSelected.delete(id);
    } else {
      nextSelected.add(id);
    }
    setSelectedIds(nextSelected);
  };

  const handleSelectAll = () => {
    if (selectedIds.size === filteredAndSortedRows.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filteredAndSortedRows.map((r) => r.project_asset_line_id)));
    }
  };

  const handleSortChange = (field: SortField) => {
    setSortState((prev) => ({
      field,
      order: prev.field === field && prev.order === "asc" ? "desc" : "asc"
    }));
  };

  // 3. Virtualization Calculations
  const handleScroll = (e: UIEvent<HTMLDivElement>) => {
    setScrollTop(e.currentTarget.scrollTop);
  };

  const startIndex = Math.max(0, Math.floor(scrollTop / rowHeight) - 2);
  const endIndex = Math.min(
    filteredAndSortedRows.length - 1,
    Math.ceil((scrollTop + containerHeight) / rowHeight) + 2
  );

  const visibleRows = useMemo(() => {
    return filteredAndSortedRows.slice(startIndex, endIndex + 1);
  }, [filteredAndSortedRows, startIndex, endIndex]);

  const totalHeight = filteredAndSortedRows.length * rowHeight;
  const offsetY = startIndex * rowHeight;

  if (rows.length === 0) {
    return <EmptyState title="Chưa có tài sản nào" message="Hãy nhập dữ liệu hoặc kiểm tra lại hồ sơ để bắt đầu." />;
  }

  return (
    <div className="asset-grid-container" style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <AssetGridToolbar
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        validationFilter={validationFilter}
        onValidationFilterChange={setValidationFilter}
        selectedCount={selectedIds.size}
      />

      {filteredAndSortedRows.length === 0 ? (
        <EmptyState />
      ) : (
        <div
          className="grid-scroll-viewport"
          onScroll={handleScroll}
          style={{
            height: `${containerHeight}px`,
            overflowY: "auto",
            border: "1px solid var(--border-color)",
            borderRadius: "var(--radius-md)",
            position: "relative",
            backgroundColor: "rgba(255, 255, 255, 0.01)"
          }}
        >
          {/* Table Container */}
          <table style={{ width: "100%", borderCollapse: "collapse", position: "relative" }}>
            <thead style={{ position: "sticky", top: 0, backgroundColor: "var(--bg-secondary)", zIndex: 10, borderBottom: "2px solid var(--border-color)" }}>
              <tr style={{ height: "45px" }}>
                <th style={{ padding: "var(--space-sm)", textAlign: "left", width: "40px" }}>
                  <input
                    type="checkbox"
                    checked={selectedIds.size > 0 && selectedIds.size === filteredAndSortedRows.length}
                    onChange={handleSelectAll}
                  />
                </th>
                <th style={{ cursor: "pointer", padding: "var(--space-sm)", textAlign: "left", width: "60px" }} onClick={() => handleSortChange("line_no")}>
                  # {sortState.field === "line_no" ? (sortState.order === "asc" ? "▲" : "▼") : ""}
                </th>
                <th style={{ cursor: "pointer", padding: "var(--space-sm)", textAlign: "left" }} onClick={() => handleSortChange("raw_name")}>
                  Raw Name {sortState.field === "raw_name" ? (sortState.order === "asc" ? "▲" : "▼") : ""}
                </th>
                <th style={{ padding: "var(--space-sm)", textAlign: "left" }}>Normalized Name</th>
                <th style={{ padding: "var(--space-sm)", textAlign: "left" }}>Canonical Asset</th>
                <th style={{ padding: "var(--space-sm)", textAlign: "left" }}>Variant</th>
                <th style={{ padding: "var(--space-sm)", textAlign: "left" }}>Taxonomy Path</th>
                <th style={{ cursor: "pointer", padding: "var(--space-sm)", textAlign: "right", width: "80px" }} onClick={() => handleSortChange("quantity")}>
                  Qty {sortState.field === "quantity" ? (sortState.order === "asc" ? "▲" : "▼") : ""}
                </th>
                <th style={{ padding: "var(--space-sm)", textAlign: "center", width: "60px" }}>Unit</th>
                <th style={{ padding: "var(--space-sm)", textAlign: "right", width: "100px" }}>Quote 1</th>
                <th style={{ padding: "var(--space-sm)", textAlign: "right", width: "100px" }}>Quote 2</th>
                <th style={{ padding: "var(--space-sm)", textAlign: "right", width: "100px" }}>Quote 3</th>
                <th style={{ padding: "var(--space-sm)", textAlign: "center", width: "60px" }}>Currency</th>
                <th style={{ cursor: "pointer", padding: "var(--space-sm)", textAlign: "right", width: "120px" }} onClick={() => handleSortChange("appraised_price")}>
                  Price {sortState.field === "appraised_price" ? (sortState.order === "asc" ? "▲" : "▼") : ""}
                </th>
                <th style={{ padding: "var(--space-sm)", textAlign: "center" }}>Trạng thái nháp</th>
                <th style={{ padding: "var(--space-sm)", textAlign: "center" }}>Validation</th>
                <th style={{ padding: "var(--space-sm)", textAlign: "center" }}>Review</th>
              </tr>
            </thead>
          </table>

          {/* Virtual height spacers */}
          <div style={{ height: `${totalHeight}px`, width: "100%", position: "absolute", top: 0, left: 0, pointerEvents: "none" }} />

          {/* Absolute offset container for actual table rows */}
          <div style={{ transform: `translateY(${offsetY}px)`, position: "absolute", left: 0, right: 0, top: 0 }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <tbody>
                {visibleRows.map((row) => {
                  const isSelected = selectedIds.has(row.project_asset_line_id);
                  const isActive = activeId === row.project_asset_line_id;
                  const rowClass = `grid-row ${isSelected ? "selected" : ""} ${isActive ? "active" : ""}`;

                  const nameDraftKey = `${row.project_asset_line_id}:normalized_name`;
                  const priceDraftKey = `${row.project_asset_line_id}:appraised_price`;

                  const nameValue = drafts[nameDraftKey]?.draft_value ?? row.normalized_name;
                  const priceValue = drafts[priceDraftKey]?.draft_value ?? row.appraised_price;

                  const isNameDirty = !!drafts[nameDraftKey];
                  const isPriceDirty = !!drafts[priceDraftKey];

                  return (
                    <tr
                      key={row.project_asset_line_id}
                      className={rowClass}
                      onClick={() => handleRowClick(row.project_asset_line_id)}
                      data-row-version={row.row_version}
                      style={{
                        height: `${rowHeight}px`,
                        borderBottom: "1px solid var(--border-color)",
                        cursor: "pointer",
                        backgroundColor: isActive
                          ? "rgba(102, 252, 241, 0.12)"
                          : isSelected
                          ? "rgba(102, 252, 241, 0.04)"
                          : "transparent"
                      }}
                    >
                      <td style={{ padding: "var(--space-sm)", textAlign: "left", width: "40px" }}>
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={(e) => {}}
                          onClick={(e) => handleCheckboxClick(e, row.project_asset_line_id)}
                        />
                      </td>
                      <td style={{ padding: "var(--space-sm)", width: "60px", color: "var(--text-muted)", fontSize: "var(--font-size-xs)" }}>
                        {row.line_no}
                      </td>
                      <td style={{ padding: "var(--space-sm)", fontWeight: 600, color: "#fff", maxWidth: "200px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={row.raw_name}>
                        {row.raw_name}
                      </td>
                      <td style={{ padding: "var(--space-sm)" }}>
                        {nameValue}
                      </td>
                      <td style={{ padding: "var(--space-sm)", color: "var(--accent-cyan)" }}>
                        {row.canonical_asset.standard_name}
                      </td>
                      <td style={{ padding: "var(--space-sm)" }}>{row.asset_variant.display_name}</td>
                      <td style={{ padding: "var(--space-sm)", fontSize: "var(--font-size-xs)", color: "var(--text-muted)", maxWidth: "150px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={row.taxonomy_node.path}>
                        {row.taxonomy_node.path}
                      </td>
                      <td style={{ padding: "var(--space-sm)", textAlign: "right", width: "80px" }}>{row.quantity}</td>
                      <td style={{ padding: "var(--space-sm)", textAlign: "center", width: "60px", color: "var(--text-muted)" }}>
                        {row.unit.name_vi}
                      </td>
                      <td style={{ padding: "var(--space-sm)", textAlign: "right", fontSize: "var(--font-size-xs)", width: "100px", color: "var(--text-muted)" }}>
                        {row.supplier_quote_1 ? row.supplier_quote_1.toLocaleString() : "—"}
                      </td>
                      <td style={{ padding: "var(--space-sm)", textAlign: "right", fontSize: "var(--font-size-xs)", width: "100px", color: "var(--text-muted)" }}>
                        {row.supplier_quote_2 ? row.supplier_quote_2.toLocaleString() : "—"}
                      </td>
                      <td style={{ padding: "var(--space-sm)", textAlign: "right", fontSize: "var(--font-size-xs)", width: "100px", color: "var(--text-muted)" }}>
                        {row.supplier_quote_3 ? row.supplier_quote_3.toLocaleString() : "—"}
                      </td>
                      <td style={{ padding: "var(--space-sm)", textAlign: "center", width: "60px", color: "var(--text-muted)" }}>
                        {row.currency.code}
                      </td>
                      <td style={{ padding: "var(--space-sm)", textAlign: "right", fontWeight: 600, width: "120px", color: "var(--accent-blue)" }}>
                        <InlineDraftCell
                          value={typeof priceValue === "number" ? priceValue.toString() : priceValue}
                          isDirty={isPriceDirty}
                          onSave={(newVal) => {
                            if (onDraftChange) {
                              const numericVal = parseInt(newVal.replace(/,/g, ""), 10);
                              onDraftChange(row.project_asset_line_id, "appraised_price", isNaN(numericVal) ? newVal : numericVal, row.appraised_price, row.row_version);
                            }
                          }}
                        />
                      </td>
                      <td style={{ padding: "var(--space-sm)", textAlign: "center" }}>
                        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "4px" }}>
                          <StatusBadge
                            status={getDraftStatusBadge(draftStates[row.project_asset_line_id]?.draft_status || "clean", !!drafts[nameDraftKey] || !!drafts[priceDraftKey])}
                            label={getDraftStatusLabelVi(draftStates[row.project_asset_line_id]?.draft_status || "clean", !!drafts[nameDraftKey] || !!drafts[priceDraftKey])}
                          />
                          {draftStates[row.project_asset_line_id]?.has_saved_draft && (
                            <button
                              onClick={() => executeDraftCommit(
                                (msg) => window.confirm(msg),
                                onCommitDraft,
                                row.project_asset_line_id,
                                row.row_version,
                                ["appraised_unit_price"],
                                "Xác nhận áp dụng nháp\n\nThao tác này sẽ cập nhật dữ liệu chính thức của dòng tài sản bằng giá trị nháp đã lưu."
                              )}
                              style={{
                                fontSize: "10px",
                                padding: "2px 6px",
                                backgroundColor: "var(--status-review)",
                                border: "none",
                                borderRadius: "3px",
                                color: "#fff",
                                cursor: "pointer"
                              }}
                            >
                              Áp dụng nháp
                            </button>
                          )}
                        </div>
                      </td>
                      <td style={{ padding: "var(--space-sm)", textAlign: "center" }}>
                        <StatusBadge
                          status={row.validation_status === "valid" ? "approved" : row.validation_status}
                          label={row.validation_status}
                        />
                      </td>
                      <td style={{ padding: "var(--space-sm)", textAlign: "center" }}>
                        <StatusBadge status={row.review_status === "approved" ? "approved" : "review"} label={row.review_status} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
