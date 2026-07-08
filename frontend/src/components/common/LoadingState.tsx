import React from "react";

interface LoadingStateProps {
  message?: string;
}

export function LoadingState({ message = "Loading workbench session..." }: LoadingStateProps) {
  return (
    <div className="state-container">
      <div className="state-title">Loading...</div>
      <p className="state-message">{message}</p>
    </div>
  );
}
