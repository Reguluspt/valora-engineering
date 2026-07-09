export type FriendlyError = {
  title: string;
  message: string;
  nextAction: string;
  severity: "info" | "warning" | "error" | "blocking";
  retryable: boolean;
};

export type ErrorCode =
  // Network / connectivity
  | "network_failure"
  | "lost_connection_during_save"
  | "request_timeout"
  | "server_unreachable"
  // Authentication / permission
  | "unauthenticated"
  | "forbidden"
  | "session_expired"
  | "insufficient_permission"
  // Data conflict / validation
  | "optimistic_conflict"
  | "validation_error"
  | "invalid_input"
  | "missing_required_field"
  | "stale_data"
  | "locked_record"
  // Import / file handling
  | "excel_parse_error"
  | "unsupported_excel_format"
  | "empty_excel_file"
  | "invalid_column_mapping"
  | "import_failed"
  // Workbench / draft save
  | "draft_save_failed"
  | "draft_restore_failed"
  | "autosave_unavailable"
  | "unsaved_changes_before_leave"
  | "official_commit_failed"
  // AI assistant
  | "assistant_timeout"
  | "assistant_unavailable"
  | "assistant_rate_limited"
  | "assistant_invalid_response"
  | "assistant_request_failed"
  // Report generation
  | "report_generation_failed"
  | "report_template_missing"
  | "report_data_not_ready"
  | "report_download_failed"
  // Generic fallback
  | "unknown_error"
  | "server_error"
  | "temporary_failure";
