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
        placeholder="Tìm kiếm theo tên..."
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
        <option value="All">Tất cả trạng thái kiểm tra</option>
        <option value="raw">Thô</option>
        <option value="parsed">Đã phân tích</option>
        <option value="approved">Đã duyệt</option>
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
        <option value="All">Tất cả trạng thái kiểm tra dữ liệu</option>
        <option value="valid">Hợp lệ</option>
        <option value="warning">Cảnh báo</option>
        <option value="error">Lỗi</option>
        <option value="blocking">Chặn</option>
      </select>
      {selectedCount > 0 && (
        <span style={{ fontSize: "var(--font-size-sm)", color: "var(--accent-cyan)" }}>
          Đã chọn {selectedCount} dòng
        </span>
      )}
    </div>
  );
}
