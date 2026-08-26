import React, { useState, useMemo } from "react";
import { ReviewQueueItem, ReviewRole } from "./ReviewQueueTypes";
import { ReviewActionPanel } from "./ReviewActionPanel";
import { StatusBadge } from "../../common/StatusBadge";
import { EmptyState } from "../../common/EmptyState";

interface ReviewQueueDashboardProps {
  items?: ReviewQueueItem[];
  currentRole?: ReviewRole | null;
  currentUserId?: string | null;
}

export function ReviewQueueDashboard({
  items = [],
  currentRole = null,
  currentUserId = null
}: ReviewQueueDashboardProps) {
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);

  // Filters state
  const [priorityFilter, setPriorityFilter] = useState("All");
  const [typeFilter, setTypeFilter] = useState("All");
  const [statusFilter, setStatusFilter] = useState("All");

  const selectedItem = useMemo(() => {
    return items.find((i) => i.id === selectedItemId) || null;
  }, [items, selectedItemId]);

  // Apply filters locally
  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      if (priorityFilter !== "All" && item.priority !== priorityFilter) return false;
      if (typeFilter !== "All" && item.review_type !== typeFilter) return false;
      if (statusFilter !== "All" && item.status !== statusFilter) return false;
      return true;
    });
  }, [items, priorityFilter, typeFilter, statusFilter]);

  // Aggregate stats counters
  const stats = useMemo(() => {
    return {
      total: items.length,
      pending: items.filter((i) => i.status !== "completed").length,
      blocking: items.filter((i) => i.validation_status === "blocking").length,
      assignedToMe: currentUserId === null
        ? 0
        : items.filter((i) => i.assigned_to === currentUserId).length
    };
  }, [currentUserId, items]);

  return (
    <div style={{ padding: "var(--space-lg)", height: "100%", display: "flex", flexDirection: "column", overflow: "hidden" }}>
      {/* Top statistics section */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--space-lg)" }}>
        <div>
          <h2 style={{ color: "#fff", margin: 0 }}>Hàng đợi rà soát</h2>
          <p style={{ color: "var(--text-muted)", margin: "var(--space-xs) 0 0 0", fontSize: "var(--font-size-sm)" }}>
            Theo dõi các nhiệm vụ cần chuyên viên kiểm tra và quyết định.
          </p>
        </div>

      </div>

      {/* Grid stats counts summary */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "var(--space-md)", marginBottom: "var(--space-lg)" }}>
        <div style={{ backgroundColor: "var(--bg-secondary)", padding: "var(--space-md)", borderRadius: "var(--radius-lg)", border: "1px solid var(--border-color)" }}>
          <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>Tổng nhiệm vụ</div>
          <div style={{ fontSize: "var(--font-size-xl)", fontWeight: "bold", color: "#fff" }}>{stats.total}</div>
        </div>
        <div style={{ backgroundColor: "var(--bg-secondary)", padding: "var(--space-md)", borderRadius: "var(--radius-lg)", border: "1px solid var(--border-color)" }}>
          <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>Đang chờ xử lý</div>
          <div style={{ fontSize: "var(--font-size-xl)", fontWeight: "bold", color: "var(--status-review)" }}>{stats.pending}</div>
        </div>
        <div style={{ backgroundColor: "var(--bg-secondary)", padding: "var(--space-md)", borderRadius: "var(--radius-lg)", border: "1px solid var(--border-color)" }}>
          <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>Đang bị chặn</div>
          <div style={{ fontSize: "var(--font-size-xl)", fontWeight: "bold", color: "var(--status-blocking)" }}>{stats.blocking}</div>
        </div>
        <div style={{ backgroundColor: "var(--bg-secondary)", padding: "var(--space-md)", borderRadius: "var(--radius-lg)", border: "1px solid var(--border-color)" }}>
          <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>Được giao cho tôi</div>
          <div style={{ fontSize: "var(--font-size-xl)", fontWeight: "bold", color: "var(--accent-cyan)" }}>{stats.assignedToMe}</div>
        </div>
      </div>

      {/* Toolbar filters list */}
      <div style={{ display: "flex", gap: "var(--space-md)", marginBottom: "var(--space-md)", alignItems: "center" }}>
        <select
          value={priorityFilter}
          onChange={(e) => setPriorityFilter(e.target.value)}
          style={{
            backgroundColor: "var(--bg-secondary)",
            border: "1px solid var(--border-color)",
            color: "var(--text-primary)",
            padding: "var(--space-sm)",
            borderRadius: "var(--radius-md)"
          }}
        >
          <option value="All">Tất cả mức ưu tiên</option>
          <option value="high">Cao</option>
          <option value="normal">Bình thường</option>
          <option value="low">Thấp</option>
        </select>

        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          style={{
            backgroundColor: "var(--bg-secondary)",
            border: "1px solid var(--border-color)",
            color: "var(--text-primary)",
            padding: "var(--space-sm)",
            borderRadius: "var(--radius-md)"
          }}
        >
          <option value="All">Tất cả loại rà soát</option>
          <option value="identity">Nhận diện tài sản</option>
          <option value="appraised_price">Giá thẩm định</option>
          <option value="taxonomy">Phân loại</option>
          <option value="qc">Kiểm soát chất lượng</option>
        </select>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          style={{
            backgroundColor: "var(--bg-secondary)",
            border: "1px solid var(--border-color)",
            color: "var(--text-primary)",
            padding: "var(--space-sm)",
            borderRadius: "var(--radius-md)"
          }}
        >
          <option value="All">Tất cả trạng thái</option>
          <option value="open">Chưa xử lý</option>
          <option value="in_review">Đang rà soát</option>
          <option value="completed">Đã hoàn tất</option>
        </select>
      </div>

      {/* Split view workspace */}
      <div style={{ flex: 1, display: "flex", gap: "var(--space-lg)", overflow: "hidden" }}>
        {/* Table Panel */}
        <div style={{ flex: 1, overflowY: "auto", border: "1px solid var(--border-color)", borderRadius: "var(--radius-lg)" }}>
          {filteredItems.length === 0 ? (
            <EmptyState
              title="Chưa có nhiệm vụ cần duyệt"
              message="Hệ thống chưa trả về nhiệm vụ phù hợp với bộ lọc hiện tại."
            />
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead style={{ backgroundColor: "var(--bg-secondary)", borderBottom: "2px solid var(--border-color)", position: "sticky", top: 0 }}>
                <tr style={{ height: "45px" }}>
                  <th style={{ padding: "var(--space-sm)", textAlign: "left" }}>Mã hồ sơ</th>
                  <th style={{ padding: "var(--space-sm)", textAlign: "left" }}>Tài sản</th>
                  <th style={{ padding: "var(--space-sm)", textAlign: "center" }}>Loại rà soát</th>
                  <th style={{ padding: "var(--space-sm)", textAlign: "center" }}>Ưu tiên</th>
                  <th style={{ padding: "var(--space-sm)", textAlign: "center" }}>Kiểm tra</th>
                  <th style={{ padding: "var(--space-sm)", textAlign: "center" }}>Người xử lý</th>
                  <th style={{ padding: "var(--space-sm)", textAlign: "center" }}>Trạng thái</th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.map((item) => {
                  const isActive = selectedItemId === item.id;
                  return (
                    <tr
                      key={item.id}
                      onClick={() => setSelectedItemId(item.id)}
                      data-row-version={item.row_version}
                      style={{
                        height: "55px",
                        borderBottom: "1px solid var(--border-color)",
                        cursor: "pointer",
                        backgroundColor: isActive ? "rgba(102, 252, 241, 0.1)" : "transparent"
                      }}
                    >
                      <td style={{ padding: "var(--space-sm)" }}>
                        <strong>{item.project_code}</strong>
                        <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>{item.project_name}</div>
                      </td>
                      <td style={{ padding: "var(--space-sm)", fontWeight: 600, color: "#fff" }}>
                        Dòng {item.line_no}: {item.asset_summary}
                      </td>
                      <td style={{ padding: "var(--space-sm)", textAlign: "center" }}>
                        <span style={{ fontSize: "var(--font-size-xs)", textTransform: "capitalize" }}>
                          {item.review_type}
                        </span>
                      </td>
                      <td style={{ padding: "var(--space-sm)", textAlign: "center" }}>
                        <span style={{
                          color: item.priority === "high"
                            ? "var(--status-error)"
                            : item.priority === "normal"
                            ? "var(--status-review)"
                            : "var(--text-muted)",
                          fontWeight: "bold",
                          textTransform: "uppercase",
                          fontSize: "var(--font-size-xs)"
                        }}>
                          {item.priority}
                        </span>
                      </td>
                      <td style={{ padding: "var(--space-sm)", textAlign: "center" }}>
                        <StatusBadge
                          status={item.validation_status === "valid" ? "approved" : item.validation_status}
                          label={item.validation_status}
                        />
                      </td>
                      <td style={{ padding: "var(--space-sm)", textAlign: "center", color: "var(--text-muted)", fontSize: "var(--font-size-xs)" }}>
                        {item.assigned_to || "Chưa phân công"}
                      </td>
                      <td style={{ padding: "var(--space-sm)", textAlign: "center" }}>
                        <span style={{
                          color: item.status === "completed" ? "var(--status-approved)" : "var(--status-draft)",
                          fontSize: "var(--font-size-xs)",
                          fontWeight: "bold"
                        }}>
                          {item.status.toUpperCase()}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Action Panel Side Draw */}
        <div style={{ width: "320px", display: "flex", flexDirection: "column" }}>
          <ReviewActionPanel item={selectedItem} currentRole={currentRole} />
        </div>
      </div>
    </div>
  );
}
