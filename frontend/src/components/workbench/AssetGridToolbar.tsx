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
    <div className="valora-command-bar grid-toolbar" role="search" aria-label="Lọc danh sách tài sản">
      <input
        className="valora-search-field"
        type="text"
        aria-label="Tìm theo tên tài sản"
        placeholder="Tìm kiếm theo tên..."
        value={searchQuery}
        onChange={(e) => onSearchChange(e.target.value)}
      />
      <select
        className="valora-select"
        aria-label="Lọc trạng thái rà soát"
        value={statusFilter}
        onChange={(e) => onStatusFilterChange(e.target.value)}
      >
        <option value="All">Tất cả trạng thái rà soát</option>
        <option value="raw">Thô</option>
        <option value="parsed">Đã phân tích</option>
        <option value="approved">Đã duyệt</option>
      </select>
      <select
        className="valora-select"
        aria-label="Lọc trạng thái kiểm tra dữ liệu"
        value={validationFilter}
        onChange={(e) => onValidationFilterChange(e.target.value)}
      >
        <option value="All">Tất cả trạng thái kiểm tra dữ liệu</option>
        <option value="valid">Hợp lệ</option>
        <option value="warning">Cảnh báo</option>
        <option value="error">Lỗi</option>
        <option value="blocking">Chặn</option>
      </select>
      {selectedCount > 0 && (
        <span className="valora-status valora-status--info" role="status">
          Đã chọn {selectedCount} dòng
        </span>
      )}
    </div>
  );
}
