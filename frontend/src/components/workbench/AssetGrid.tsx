import React, { useState, useMemo, UIEvent } from "react";
import { AssetLineGridRow, GridSortState, SortField } from "./AssetGridTypes";
import { AssetGridToolbar } from "./AssetGridToolbar";
import { StatusBadge } from "../common/StatusBadge";
import { InlineDraftCell } from "./drafts/InlineDraftCell";
import { EmptyState } from "../common/EmptyState";

import { InlineEditDraft } from "./drafts/DraftStateTypes";
import { getDraftStatusLabelVi, getDraftStatusBadge } from "./hooks/useWorkbenchDraftState";

const VALIDATION_LABELS: Record<string, string> = {
  valid: "Hợp lệ",
  warning: "Cảnh báo",
  error: "Lỗi",
  blocking: "Chặn",
  unvalidated: "Chưa kiểm tra",
  needs_review: "Cần kiểm tra",
};

const REVIEW_LABELS: Record<string, string> = {
  raw: "Thô",
  parsed: "Đã phân tích",
  identity_suggested: "Đề xuất định danh",
  identity_approved: "Đã định danh",
  taxonomy_approved: "Đã phân loại",
  knowledge_matched: "Đã khớp dữ liệu",
  price_reviewed: "Đã thẩm định giá",
  approved: "Đã duyệt",
  locked: "Đã khóa",
  excluded: "Đã loại",
};

const UNKNOWN_LABEL = "Chưa xác định";

function validationLabel(v: string | null | undefined): string {
  if (v === null || v === undefined) return UNKNOWN_LABEL;
  return VALIDATION_LABELS[v] ?? UNKNOWN_LABEL;
}

function reviewLabel(v: string | null | undefined): string {
  if (v === null || v === undefined) return UNKNOWN_LABEL;
  return REVIEW_LABELS[v] ?? UNKNOWN_LABEL;
}

export { validationLabel, reviewLabel, VALIDATION_LABELS, REVIEW_LABELS, UNKNOWN_LABEL };

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
    <div className="asset-grid-container">
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
        <EmptyState title="Không có tài sản phù hợp" message="Hãy thay đổi từ khóa hoặc bộ lọc để xem các dòng tài sản khác." />
      ) : (
        <div
          className="grid-scroll-viewport valora-table-shell"
          onScroll={handleScroll}
          style={{ height: `${containerHeight}px` }}
        >
          {/* Table Container */}
          <table className="valora-table asset-grid-table asset-grid-table--header" aria-label="Tiêu đề danh sách tài sản">
            <thead>
              <tr>
                <th className="asset-grid-col-check">
                  <input
                    type="checkbox"
                    aria-label="Chọn tất cả dòng đang hiển thị"
                    checked={selectedIds.size > 0 && selectedIds.size === filteredAndSortedRows.length}
                    onChange={handleSelectAll}
                  />
                </th>
                <th className="asset-grid-col-number" aria-sort={sortState.field === "line_no" ? (sortState.order === "asc" ? "ascending" : "descending") : "none"}>
                  <button type="button" className="asset-grid-sort" onClick={() => handleSortChange("line_no")}>
                    # {sortState.field === "line_no" ? (sortState.order === "asc" ? "▲" : "▼") : ""}
                  </button>
                </th>
                  <th aria-sort={sortState.field === "raw_name" ? (sortState.order === "asc" ? "ascending" : "descending") : "none"}>
                    <button type="button" className="asset-grid-sort" onClick={() => handleSortChange("raw_name")}>
                      Tên gốc {sortState.field === "raw_name" ? (sortState.order === "asc" ? "▲" : "▼") : ""}
                    </button>
                  </th>
                  <th>Tên chuẩn hóa</th>
                  <th>Tài sản chuẩn</th>
                  <th>Biến thể</th>
                  <th>Phân loại</th>
                  <th className="asset-grid-col-quantity" aria-sort={sortState.field === "quantity" ? (sortState.order === "asc" ? "ascending" : "descending") : "none"}>
                    <button type="button" className="asset-grid-sort asset-grid-sort--numeric" onClick={() => handleSortChange("quantity")}>
                      SL {sortState.field === "quantity" ? (sortState.order === "asc" ? "▲" : "▼") : ""}
                    </button>
                  </th>
                  <th className="asset-grid-col-unit">Đơn vị</th>
                  <th className="asset-grid-col-quote">Báo giá 1</th>
                  <th className="asset-grid-col-quote">Báo giá 2</th>
                  <th className="asset-grid-col-quote">Báo giá 3</th>
                  <th className="asset-grid-col-unit">Tiền tệ</th>
                  <th className="asset-grid-col-price" aria-sort={sortState.field === "appraised_price" ? (sortState.order === "asc" ? "ascending" : "descending") : "none"}>
                    <button type="button" className="asset-grid-sort asset-grid-sort--numeric" onClick={() => handleSortChange("appraised_price")}>
                      Giá TĐ {sortState.field === "appraised_price" ? (sortState.order === "asc" ? "▲" : "▼") : ""}
                    </button>
                  </th>
                  <th>Trạng thái nháp</th>
                  <th>Kiểm tra dữ liệu</th>
                  <th>Trạng thái rà soát</th>
              </tr>
            </thead>
          </table>

          {/* Virtual height spacers */}
          <div className="asset-grid-virtual-spacer" style={{ height: `${totalHeight}px` }} />

          {/* Absolute offset container for actual table rows */}
          <div className="asset-grid-virtual-rows" style={{ transform: `translateY(${offsetY}px)` }}>
            <table className="valora-table asset-grid-table" aria-label="Danh sách tài sản">
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
                      onKeyDown={(event) => {
                        if (event.target === event.currentTarget && (event.key === "Enter" || event.key === " ")) {
                          event.preventDefault();
                          handleRowClick(row.project_asset_line_id);
                        }
                      }}
                      tabIndex={0}
                      aria-label={`Tài sản dòng ${row.line_no}: ${row.raw_name}`}
                      aria-selected={isSelected}
                      data-active={isActive}
                      data-row-version={row.row_version}
                    >
                      <td className="asset-grid-col-check">
                        <input
                          type="checkbox"
                          aria-label={`Chọn dòng ${row.line_no}: ${row.raw_name}`}
                          checked={isSelected}
                          onChange={(e) => {}}
                          onClick={(e) => handleCheckboxClick(e, row.project_asset_line_id)}
                        />
                      </td>
                      <td className="asset-grid-col-number asset-grid-muted">
                        {row.line_no}
                      </td>
                      <td className="asset-grid-name" title={row.raw_name}>
                        <span className="asset-grid-name-content">
                          <span className="asset-grid-name-text">{row.raw_name}</span>
                          {isActive && <span className="asset-grid-active-label">Đang xem</span>}
                        </span>
                      </td>
                      <td className="asset-grid-muted">
                        {nameValue ?? "—"}
                      </td>
                      <td>
                        {row.canonical_asset?.standard_name ?? "—"}
                      </td>
                      <td className="asset-grid-muted">{row.asset_variant?.display_name ?? "—"}</td>
                      <td className="asset-grid-taxonomy asset-grid-muted" title={row.taxonomy_node?.path ?? ""}>
                        {row.taxonomy_node?.path ?? "Chưa phân loại"}
                      </td>
                      <td className="asset-grid-col-quantity">{row.quantity}</td>
                      <td className="asset-grid-col-unit asset-grid-muted">
                        {row.unit?.name_vi ?? "—"}
                      </td>
                      <td className="asset-grid-col-quote asset-grid-muted">
                        {row.supplier_quote_1 != null ? row.supplier_quote_1.toLocaleString() : "—"}
                      </td>
                      <td className="asset-grid-col-quote asset-grid-muted">
                        {row.supplier_quote_2 != null ? row.supplier_quote_2.toLocaleString() : "—"}
                      </td>
                      <td className="asset-grid-col-quote asset-grid-muted">
                        {row.supplier_quote_3 != null ? row.supplier_quote_3.toLocaleString() : "—"}
                      </td>
                      <td className="asset-grid-col-unit asset-grid-muted">
                        {row.currency?.code ?? "—"}
                      </td>
                      <td className="asset-grid-col-price">
                        <InlineDraftCell
                          value={priceValue != null ? (typeof priceValue === "number" ? priceValue.toString() : priceValue) : "—"}
                          isDirty={isPriceDirty}
                          onSave={(newVal) => {
                            if (onDraftChange && row.row_version != null) {
                              const numericVal = parseInt(newVal.replace(/,/g, ""), 10);
                              onDraftChange(row.project_asset_line_id, "appraised_price", isNaN(numericVal) ? newVal : numericVal, row.appraised_price, row.row_version);
                            }
                          }}
                        />
                      </td>
                      <td className="asset-grid-status-cell">
                        <div className="asset-grid-draft-status">
                          <StatusBadge
                            status={getDraftStatusBadge(draftStates[row.project_asset_line_id]?.draft_status || "clean", !!drafts[nameDraftKey] || !!drafts[priceDraftKey])}
                            label={getDraftStatusLabelVi(draftStates[row.project_asset_line_id]?.draft_status || "clean", !!drafts[nameDraftKey] || !!drafts[priceDraftKey])}
                          />
                          {draftStates[row.project_asset_line_id]?.has_saved_draft && row.row_version != null && (
                            <button
                              onClick={(event) => {
                                event.stopPropagation();
                                if (row.row_version == null) return;
                                executeDraftCommit(
                                  (msg) => window.confirm(msg),
                                  onCommitDraft,
                                  row.project_asset_line_id,
                                  row.row_version,
                                  ["appraised_unit_price"],
                                  "Xác nhận áp dụng nháp\n\nThao tác này sẽ cập nhật dữ liệu chính thức của dòng tài sản bằng giá trị nháp đã lưu."
                                )
                              }}
                              className="valora-button valora-button--secondary asset-grid-commit"
                            >
                              Áp dụng nháp
                            </button>
                          )}
                        </div>
                      </td>
                      <td className="asset-grid-status-cell">
                        <StatusBadge
                          status={row.validation_status === "valid" ? "approved" : row.validation_status}
                          label={validationLabel(row.validation_status)}
                        />
                      </td>
                      <td className="asset-grid-status-cell">
                        <StatusBadge status={row.review_status === "approved" ? "approved" : "review"} label={reviewLabel(row.review_status)} />
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
