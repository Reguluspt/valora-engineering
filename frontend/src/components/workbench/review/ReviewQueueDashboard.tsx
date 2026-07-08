import React, { useState, useMemo } from "react";
import { ReviewQueueItem, MockRole } from "./ReviewQueueTypes";
import { MOCK_REVIEW_QUEUE } from "./mockReviewQueue";
import { ReviewActionPanel } from "./ReviewActionPanel";
import { StatusBadge } from "../../common/StatusBadge";
import { EmptyState } from "../../common/EmptyState";

export function ReviewQueueDashboard() {
  const [items, setItems] = useState<ReviewQueueItem[]>(MOCK_REVIEW_QUEUE);
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);

  // Filters state
  const [priorityFilter, setPriorityFilter] = useState("All");
  const [typeFilter, setTypeFilter] = useState("All");
  const [statusFilter, setStatusFilter] = useState("All");

  // Mock User Role switcher state
  const [mockRole, setMockRole] = useState<MockRole>("reviewer");

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
      assignedToMe: items.filter((i) => i.assigned_to === "reviewer_1").length
    };
  }, [items]);

  return (
    <div style={{ padding: "var(--space-lg)", height: "100%", display: "flex", flexDirection: "column", overflow: "hidden" }}>
      {/* Top statistics section */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--space-lg)" }}>
        <div>
          <h2 style={{ color: "#fff", margin: 0 }}>Review Queue Dashboard</h2>
          <p style={{ color: "var(--text-muted)", margin: "var(--space-xs) 0 0 0", fontSize: "var(--font-size-sm)" }}>
            Centralized hub for project appraisal verification tasks.
          </p>
        </div>

        {/* Mock Role Switcher Dropdown */}
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-sm)", backgroundColor: "var(--bg-secondary)", padding: "var(--space-sm) var(--space-md)", borderRadius: "var(--radius-lg)", border: "1px solid var(--border-color)" }}>
          <span style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>Mock Role Context:</span>
          <select
            value={mockRole}
            onChange={(e) => setMockRole(e.target.value as MockRole)}
            style={{
              backgroundColor: "var(--bg-primary)",
              border: "1px solid var(--border-color)",
              color: "var(--accent-cyan)",
              padding: "4px 8px",
              borderRadius: "var(--radius-md)",
              fontWeight: 600
            }}
          >
            <option value="viewer">Viewer</option>
            <option value="appraiser">Appraiser</option>
            <option value="reviewer">Reviewer</option>
            <option value="admin">Admin</option>
          </select>
        </div>
      </div>

      {/* Grid stats counts summary */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "var(--space-md)", marginBottom: "var(--space-lg)" }}>
        <div style={{ backgroundColor: "var(--bg-secondary)", padding: "var(--space-md)", borderRadius: "var(--radius-lg)", border: "1px solid var(--border-color)" }}>
          <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>Total Queue Items</div>
          <div style={{ fontSize: "var(--font-size-xl)", fontWeight: "bold", color: "#fff" }}>{stats.total}</div>
        </div>
        <div style={{ backgroundColor: "var(--bg-secondary)", padding: "var(--space-md)", borderRadius: "var(--radius-lg)", border: "1px solid var(--border-color)" }}>
          <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>Pending Claims</div>
          <div style={{ fontSize: "var(--font-size-xl)", fontWeight: "bold", color: "var(--status-review)" }}>{stats.pending}</div>
        </div>
        <div style={{ backgroundColor: "var(--bg-secondary)", padding: "var(--space-md)", borderRadius: "var(--radius-lg)", border: "1px solid var(--border-color)" }}>
          <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>Gate Blocked Tasks</div>
          <div style={{ fontSize: "var(--font-size-xl)", fontWeight: "bold", color: "var(--status-blocking)" }}>{stats.blocking}</div>
        </div>
        <div style={{ backgroundColor: "var(--bg-secondary)", padding: "var(--space-md)", borderRadius: "var(--radius-lg)", border: "1px solid var(--border-color)" }}>
          <div style={{ fontSize: "var(--font-size-xs)", color: "var(--text-muted)" }}>Assigned to Me (Mock)</div>
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
          <option value="All">All Priorities</option>
          <option value="high">High</option>
          <option value="normal">Normal</option>
          <option value="low">Low</option>
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
          <option value="All">All Types</option>
          <option value="identity">Identity</option>
          <option value="appraised_price">Appraised Price</option>
          <option value="taxonomy">Taxonomy</option>
          <option value="qc">QC Review</option>
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
          <option value="All">All Statuses</option>
          <option value="open">Open</option>
          <option value="in_review">In Review</option>
          <option value="completed">Completed</option>
        </select>
      </div>

      {/* Split view workspace */}
      <div style={{ flex: 1, display: "flex", gap: "var(--space-lg)", overflow: "hidden" }}>
        {/* Table Panel */}
        <div style={{ flex: 1, overflowY: "auto", border: "1px solid var(--border-color)", borderRadius: "var(--radius-lg)" }}>
          {filteredItems.length === 0 ? (
            <EmptyState title="No queue items match filter queries." />
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead style={{ backgroundColor: "var(--bg-secondary)", borderBottom: "2px solid var(--border-color)", position: "sticky", top: 0 }}>
                <tr style={{ height: "45px" }}>
                  <th style={{ padding: "var(--space-sm)", textAlign: "left" }}>Project Code</th>
                  <th style={{ padding: "var(--space-sm)", textAlign: "left" }}>Asset Summary</th>
                  <th style={{ padding: "var(--space-sm)", textAlign: "center" }}>Review Type</th>
                  <th style={{ padding: "var(--space-sm)", textAlign: "center" }}>Priority</th>
                  <th style={{ padding: "var(--space-sm)", textAlign: "center" }}>Validation</th>
                  <th style={{ padding: "var(--space-sm)", textAlign: "center" }}>Assigned</th>
                  <th style={{ padding: "var(--space-sm)", textAlign: "center" }}>Status</th>
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
                        Line #{item.line_no}: {item.asset_summary}
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
                        {item.assigned_to || "Unassigned"}
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
          <ReviewActionPanel item={selectedItem} currentRole={mockRole} />
        </div>
      </div>
    </div>
  );
}
