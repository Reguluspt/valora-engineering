import React from "react";

interface AssetGridToolbarProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  statusFilter: string;
  onStatusFilterChange: (status: string) => void;
  validationFilter: string;
  onValidationFilterChange: (status: string) => void;
  selectedCount: number;
}

export function AssetGridToolbar({
  searchQuery,
  onSearchChange,
  statusFilter,
  onStatusFilterChange,
  validationFilter,
  onValidationFilterChange,
  selectedCount
}: AssetGridToolbarProps) {
  return (
    <div className="grid-toolbar" style={{ display: "flex", gap: "var(--space-md)", alignItems: "center", marginBottom: "var(--space-md)", flexWrap: "wrap" }}>
      <input
        type="text"
        placeholder="Search raw name..."
        value={searchQuery}
        onChange={(e) => onSearchChange(e.target.value)}
        style={{
          backgroundColor: "var(--bg-secondary)",
          border: "1px solid var(--border-color)",
          color: "var(--text-primary)",
          padding: "var(--space-sm) var(--space-md)",
          borderRadius: "var(--radius-md)",
          minWidth: "240px"
        }}
      />
      <select
        value={statusFilter}
        onChange={(e) => onStatusFilterChange(e.target.value)}
        style={{
          backgroundColor: "var(--bg-secondary)",
          border: "1px solid var(--border-color)",
          color: "var(--text-primary)",
          padding: "var(--space-sm)",
          borderRadius: "var(--radius-md)"
        }}
      >
        <option value="All">All Review Statuses</option>
        <option value="raw">Raw</option>
        <option value="parsed">Parsed</option>
        <option value="approved">Approved</option>
      </select>
      <select
        value={validationFilter}
        onChange={(e) => onValidationFilterChange(e.target.value)}
        style={{
          backgroundColor: "var(--bg-secondary)",
          border: "1px solid var(--border-color)",
          color: "var(--text-primary)",
          padding: "var(--space-sm)",
          borderRadius: "var(--radius-md)"
        }}
      >
        <option value="All">All Validation Statuses</option>
        <option value="valid">Valid</option>
        <option value="warning">Warning</option>
        <option value="error">Error</option>
        <option value="blocking">Blocking</option>
      </select>
      {selectedCount > 0 && (
        <span style={{ fontSize: "var(--font-size-sm)", color: "var(--accent-cyan)" }}>
          {selectedCount} row(s) selected
        </span>
      )}
    </div>
  );
}
