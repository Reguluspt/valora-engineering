import { FriendlyError, ErrorCode } from "./errorTypes";

export const ERROR_REGISTRY: Record<ErrorCode, FriendlyError> = {
  // Network / connectivity
  network_failure: {
    title: "Không thể kết nối với máy chủ",
    message: "Hệ thống chưa thể gửi yêu cầu của anh/chị đến máy chủ.",
    nextAction: "Vui lòng kiểm tra kết nối mạng hoặc thử lại sau ít phút.",
    severity: "error",
    retryable: true
  },
  lost_connection_during_save: {
    title: "Lưu nháp thất bại do mất kết nối",
    message: "Bản nháp của bạn đã được sao lưu tạm thời trên trình duyệt.",
    nextAction: "Hệ thống sẽ tự động gửi lại khi có mạng kết nối ổn định.",
    severity: "warning",
    retryable: true
  },
  request_timeout: {
    title: "Kết nối quá hạn",
    message: "Yêu cầu mất quá nhiều thời gian để nhận phản hồi từ hệ thống.",
    nextAction: "Vui lòng kiểm tra lại đường truyền mạng và thực hiện lại.",
    severity: "error",
    retryable: true
  },
  server_unreachable: {
    title: "Máy chủ tạm thời dừng hoạt động",
    message: "Hệ thống không thể định vị địa chỉ máy chủ dịch vụ.",
    nextAction: "Vui lòng liên hệ bộ phận kỹ thuật để được hỗ trợ kiểm tra.",
    severity: "blocking",
    retryable: false
  },

  // Authentication / permission
  unauthenticated: {
    title: "Phiên làm việc đã hết hạn",
    message: "Hệ thống yêu cầu xác thực lại danh tính tài khoản.",
    nextAction: "Vui lòng đăng nhập lại để tiếp tục bàn làm việc.",
    severity: "blocking",
    retryable: false
  },
  forbidden: {
    title: "Tài khoản chưa được cấp quyền thực hiện thao tác này",
    message: "Anh/chị không có vai trò hoặc quyền hạn tương ứng trong dự án.",
    nextAction: "Vui lòng liên hệ Quản trị viên để đăng ký vai trò phù hợp.",
    severity: "error",
    retryable: false
  },
  session_expired: {
    title: "Phiên làm việc đã hết hạn",
    message: "Xác thực phiên kết nối của bạn đã kết thúc.",
    nextAction: "Vui lòng đăng nhập lại để làm việc tiếp.",
    severity: "blocking",
    retryable: false
  },
  insufficient_permission: {
    title: "Không có quyền truy cập",
    message: "Tài khoản không sở hữu quyền thực thi hành động này.",
    nextAction: "Vui lòng liên hệ bộ phận quản lý hồ sơ để kiểm tra phân quyền.",
    severity: "error",
    retryable: false
  },

  // Data conflict / validation
  optimistic_conflict: {
    title: "Dữ liệu hồ sơ này đã được thay đổi bởi người dùng khác",
    message: "Một người dùng khác đã cập nhật trạng thái hoặc thông tin phiên làm việc từ trước.",
    nextAction: "Vui lòng bấm 'Cập nhật mới' để tải lại dữ liệu mới nhất trước khi chỉnh sửa.",
    severity: "error",
    retryable: true
  },
  validation_error: {
    title: "Thông tin nhập vào chưa đúng định dạng",
    message: "Các trường dữ liệu khai báo thẩm định vi phạm quy tắc hệ thống.",
    nextAction: "Vui lòng kiểm tra lại các trường được đánh dấu đỏ trên màn hình.",
    severity: "warning",
    retryable: false
  },
  invalid_input: {
    title: "Thông tin nhập vào chưa đúng định dạng",
    message: "Hệ thống phát hiện kiểu giá trị không tương thích.",
    nextAction: "Vui lòng sửa đổi lại thông số nhập liệu.",
    severity: "warning",
    retryable: false
  },
  missing_required_field: {
    title: "Thiếu thông tin bắt buộc",
    message: "Một hoặc nhiều thông số thẩm định chưa được điền thông tin.",
    nextAction: "Vui lòng điền đầy đủ các mục đánh dấu bắt buộc để tiếp tục.",
    severity: "warning",
    retryable: false
  },
  stale_data: {
    title: "Dữ liệu phiên làm việc đã cũ",
    message: "Bản ghi hiện tại không còn khớp với cơ sở dữ liệu gốc.",
    nextAction: "Vui lòng làm mới trang để đồng bộ lại thông tin.",
    severity: "warning",
    retryable: true
  },
  locked_record: {
    title: "Hồ sơ đang bị khóa",
    message: "Dòng tài sản này đang được khóa để thẩm định bởi thành viên khác.",
    nextAction: "Vui lòng quay lại kiểm tra sau khi phiên làm việc kết thúc.",
    severity: "blocking",
    retryable: false
  },

  // Import / file handling
  excel_parse_error: {
    title: "Tệp Excel tải lên không hợp lệ",
    message: "Tiến trình đọc cấu trúc bảng tệp Excel thất bại.",
    nextAction: "Vui lòng kiểm tra lại định dạng tệp hoặc các cột dữ liệu theo tệp mẫu.",
    severity: "error",
    retryable: true
  },
  unsupported_excel_format: {
    title: "Định dạng tệp không được hỗ trợ",
    message: "Tệp tải lên không khớp với phần mở rộng cho phép.",
    nextAction: "Vui lòng chỉ tải lên các tệp có đuôi mở rộng .xlsx hoặc .xls.",
    severity: "warning",
    retryable: false
  },
  empty_excel_file: {
    title: "Tệp Excel trống",
    message: "Hệ thống không tìm thấy dòng dữ liệu tài sản nào trong tệp tải lên.",
    nextAction: "Vui lòng điền nội dung danh sách tài sản vào tệp và tải lên lại.",
    severity: "warning",
    retryable: false
  },
  invalid_column_mapping: {
    title: "Ghép cột dữ liệu thất bại",
    message: "Các cột tiêu đề trong tệp không khớp với cấu trúc hệ thống.",
    nextAction: "Vui lòng ghép lại các trường tương ứng thủ công trên bảng điều khiển.",
    severity: "warning",
    retryable: false
  },
  import_failed: {
    title: "Nhập dữ liệu thất bại",
    message: "Lỗi phát sinh trong quá trình chuyển đổi dữ liệu Excel vào hồ sơ.",
    nextAction: "Vui lòng kiểm tra lại chất lượng dữ liệu dòng tài sản.",
    severity: "error",
    retryable: true
  },

  // Workbench / draft save
  draft_save_failed: {
    title: "Không thể lưu bản nháp",
    message: "Hệ thống gặp sự cố lưu các bản ghi tạm thời.",
    nextAction: "Vui lòng bấm nút Lưu nháp thủ công hoặc thử lại.",
    severity: "error",
    retryable: true
  },
  draft_restore_failed: {
    title: "Khôi phục bản nháp thất bại",
    message: "Bản sao lưu tạm trên trình duyệt không khả dụng hoặc bị hỏng.",
    nextAction: "Anh/chị vui lòng tải lại phiên hồ sơ gốc từ máy chủ.",
    severity: "error",
    retryable: true
  },
  autosave_unavailable: {
    title: "Tính năng tự động lưu tạm ngưng",
    message: "Hệ thống không thể khởi động tiến trình tự động lưu nháp.",
    nextAction: "Vui lòng lưu bản ghi thủ công để phòng mất mát dữ liệu.",
    severity: "warning",
    retryable: false
  },
  unsaved_changes_before_leave: {
    title: "Bạn có các thay đổi chưa được lưu",
    message: "Các chỉnh sửa thẩm định tạm thời sẽ bị mất nếu rời đi.",
    nextAction: "Bấm 'Quay lại' để lưu nháp, hoặc 'Rời đi' để hủy bỏ thay đổi.",
    severity: "warning",
    retryable: false
  },
  official_commit_failed: {
    title: "Lưu thay đổi chính thức thất bại",
    message: "Tiến trình lưu chuyển tiếp dữ liệu lên hệ thống chính thức gặp lỗi.",
    nextAction: "Vui lòng rà soát lại các cảnh báo lỗi còn tồn đọng trước khi lưu.",
    severity: "error",
    retryable: true
  },

  // AI assistant
  assistant_timeout: {
    title: "Trợ lý Valora phản hồi chậm",
    message: "Mô hình ngôn ngữ phân tích thông minh đang quá tải.",
    nextAction: "Vui lòng gửi lại câu hỏi hoặc thử lại sau ít phút.",
    severity: "warning",
    retryable: true
  },
  assistant_unavailable: {
    title: "Trợ lý Valora tạm thời không khả dụng",
    message: "Kết nối dịch vụ hỗ trợ thông minh đang tạm bảo trì.",
    nextAction: "Anh/chị vẫn có thể tiếp tục thực hiện nhập giá và điền hồ sơ thủ công.",
    severity: "warning",
    retryable: false
  },
  assistant_rate_limited: {
    title: "Yêu cầu Trợ lý Valora quá thường xuyên",
    message: "Tài khoản của bạn tạm thời đạt giới hạn lượt hỏi trong thời gian ngắn.",
    nextAction: "Vui lòng đợi vài giây và tiếp tục hỏi lại.",
    severity: "warning",
    retryable: true
  },
  assistant_invalid_response: {
    title: "Phản hồi từ Trợ lý Valora không hợp lệ",
    message: "Kết quả gợi ý thông minh gặp lỗi cấu trúc dữ liệu.",
    nextAction: "Vui lòng yêu cầu phân tích lại dòng tài sản tương ứng.",
    severity: "warning",
    retryable: true
  },
  assistant_request_failed: {
    title: "Yêu cầu Trợ lý Valora thất bại",
    message: "Lỗi kết nối hoặc xử lý prompt thông minh từ máy chủ.",
    nextAction: "Vui lòng gửi lại yêu cầu trợ giúp.",
    severity: "error",
    retryable: true
  },

  // Report generation
  report_generation_failed: {
    title: "Không thể tạo báo cáo",
    message: "Lỗi biên dịch xuất bản báo cáo nháp từ hệ thống biểu mẫu.",
    nextAction: "Vui lòng kiểm tra lại dữ liệu và cấu trúc thông tin hồ sơ.",
    severity: "error",
    retryable: true
  },
  report_template_missing: {
    title: "Thiếu mẫu báo cáo thẩm định",
    message: "Hệ thống không tìm thấy mẫu báo cáo định cấu hình tương ứng.",
    nextAction: "Vui lòng liên hệ bộ phận hỗ trợ kỹ thuật để bổ sung mẫu.",
    severity: "error",
    retryable: false
  },
  report_data_not_ready: {
    title: "Dữ liệu hồ sơ chưa sẵn sàng",
    message: "Báo cáo nháp chỉ được xuất khi hoàn thành rà soát các trường dữ liệu.",
    nextAction: "Vui lòng kiểm tra lại dữ liệu và khắc phục hết lỗi trước khi xuất báo cáo.",
    severity: "warning",
    retryable: false
  },
  report_download_failed: {
    title: "Tải báo cáo thất bại",
    message: "Kết nối tải tệp báo cáo định dạng PDF/Word gặp sự cố.",
    nextAction: "Vui lòng tải lại trang và thực hiện tải xuống lại.",
    severity: "error",
    retryable: true
  },

  // Generic fallback
  unknown_error: {
    title: "Hệ thống gặp sự cố không xác định",
    message: "Có lỗi xảy ra trong quá trình thực thi thao tác.",
    nextAction: "Vui lòng thử lại sau hoặc liên hệ hỗ trợ để được trợ giúp.",
    severity: "error",
    retryable: true
  },
  server_error: {
    title: "Hệ thống gặp lỗi xử lý nội bộ",
    message: "Thao tác gửi dữ liệu không thành công do máy chủ gặp sự cố.",
    nextAction: "Vui lòng thử lại sau vài phút.",
    severity: "error",
    retryable: true
  },
  temporary_failure: {
    title: "Thao tác tạm thời thất bại",
    message: "Dịch vụ hệ thống phản hồi không thành công.",
    nextAction: "Vui lòng thực hiện lại.",
    severity: "warning",
    retryable: true
  }
};

export function getFriendlyError(code: ErrorCode): FriendlyError {
  return ERROR_REGISTRY[code] ?? ERROR_REGISTRY.unknown_error;
}

export function getFriendlyErrorFromHttpStatus(status: number): FriendlyError {
  switch (status) {
    case 401:
      return ERROR_REGISTRY.session_expired;
    case 403:
      return ERROR_REGISTRY.forbidden;
    case 409:
      return ERROR_REGISTRY.optimistic_conflict;
    case 422:
      return ERROR_REGISTRY.validation_error;
    case 500:
      return ERROR_REGISTRY.server_error;
    default:
      return ERROR_REGISTRY.unknown_error;
  }
}

export function getFriendlyErrorFromUnknown(error: any): FriendlyError {
  if (!error) {
    return ERROR_REGISTRY.unknown_error;
  }

  // Handle standard HTTP class wrappers
  if (typeof error.status === "number") {
    return getFriendlyErrorFromHttpStatus(error.status);
  }

  // Parse string error logs safely
  const errString = String(error).toLowerCase();
  if (errString.includes("network") || errString.includes("fetch") || errString.includes("failed to fetch")) {
    return ERROR_REGISTRY.network_failure;
  }
  if (errString.includes("timeout")) {
    return ERROR_REGISTRY.request_timeout;
  }

  return ERROR_REGISTRY.unknown_error;
}
