import React, { useState } from "react";

import { ReviewQueueDashboard } from "../components/workbench/review/ReviewQueueDashboard";
import { ReviewRole } from "../components/workbench/review/ReviewQueueTypes";
import { DEMO_REVIEW_QUEUE } from "./fixtures/reviewQueue";

const DEMO_NOTICE = "DỮ LIỆU MINH HỌA — KHÔNG PHẢI HỒ SƠ THẬT";

export function DemoReviewQueuePage() {
  const [role, setRole] = useState<ReviewRole>("reviewer");

  return (
    <main style={{ minHeight: "100vh", background: "var(--bg-primary)", color: "var(--text-primary)" }}>
      <div
        data-testid="demo-data-banner"
        role="status"
        style={{
          padding: "var(--space-sm) var(--space-lg)",
          background: "var(--status-blocking)",
          color: "#fff",
          fontWeight: 700,
          letterSpacing: "0.04em",
          textAlign: "center"
        }}
      >
        {DEMO_NOTICE}
      </div>

      <div style={{ padding: "var(--space-md) var(--space-lg) 0" }}>
        <label style={{ display: "inline-flex", alignItems: "center", gap: "var(--space-sm)" }}>
          <span>Vai trò minh họa:</span>
          <select value={role} onChange={(event) => setRole(event.target.value as ReviewRole)}>
            <option value="viewer">Người xem</option>
            <option value="appraiser">Thẩm định viên</option>
            <option value="reviewer">Người rà soát</option>
            <option value="admin">Quản trị viên</option>
          </select>
        </label>
      </div>

      <ReviewQueueDashboard
        items={DEMO_REVIEW_QUEUE}
        currentRole={role}
        currentUserId="demo-reviewer"
      />
    </main>
  );
}
