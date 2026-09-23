import React from "react";
import { StateSurface } from "../ui/StateSurface";

interface LoadingStateProps {
  scope?: "initial" | "section";
  message?: string;
}

export function LoadingState({
  scope = "initial",
  message = "Vui lòng chờ trong giây lát.",
}: LoadingStateProps) {
  return (
    <StateSurface
      message={message}
      state={scope === "section" ? "SECTION_LOADING" : "INITIAL_LOADING"}
      title={scope === "section" ? "Đang cập nhật mục này" : "Đang tải nội dung"}
      titleClassName="valora-state__title valora-loading"
    />
  );
}
