# Valora Astryx Token & Component Mapping

This document establishes the UI/UX design-system contract mapping for the Project Valora MVP screens using the Astryx Design System guidelines.

---

## 1. Current Frontend UI Inventory
- **Astryx Package Status**: **Not Installed**. Dependencies in `package.json` are limited to React 18, Vite 5, and TypeScript 5. 
- **Styling Architecture**: Custom CSS defined in [index.css](file:///E:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/src/index.css) utilizing custom CSS variables (`--bg-primary`, `--bg-secondary`, `--accent-cyan`, `--status-draft`).
- **Component Implementations**: Custom vanilla React components located under `src/components/common` (e.g., `ApiErrorBanner`, `RbacLockNotice`, `StatusBadge`).
- **Integration Plan**: In future sprints, the actual Astryx design tokens and components must be installed/configured. This mapping acts as the transition registry.

---

## 2. Astryx Usage Principles
- **No Custom Patterns**: Use Astryx components whenever a matching UI layout is available. Custom overrides must be documented.
- **Vietnamese-First i18n**: User-facing English labels are strictly forbidden. All labels must map to localized Vietnamese terms in i18n dictionaries.
- **Error Masking Policy**: Technical/SQL/API error logs are strictly hidden from non-IT end-users. All technical exceptions map to clean Vietnamese warning boxes with next-action buttons.

---

## 3. Token Mapping

| Semantics | Custom CSS Variable | Astryx Target Token (TBD/Pending Confirmation) |
| :--- | :--- | :--- |
| **Page Title** | `--font-size-xl` (24px) | `Astryx semantic token TBD — pending official Astryx package/docs confirmation` |
| **Section Title** | `--font-size-lg` (18px) | `Astryx semantic token TBD — pending official Astryx package/docs confirmation` |
| **Body Text** | `--font-size-md` (16px) | `Astryx semantic token TBD — pending official Astryx package/docs confirmation` |
| **Helper Text** | `--font-size-sm` (14px) | `Astryx semantic token TBD — pending official Astryx package/docs confirmation` |
| **Error Text** | `--font-size-xs` (12px) | `Astryx semantic token TBD — pending official Astryx package/docs confirmation` |
| **Table Header** | Custom (14px Bold) | `Astryx semantic token TBD — pending official Astryx package/docs confirmation` |
| **Table Cell** | `--font-size-sm` (14px) | `Astryx semantic token TBD — pending official Astryx package/docs confirmation` |
| **Page Padding** | `--space-lg` (24px) | `Astryx semantic token TBD — pending official Astryx package/docs confirmation` |
| **Section Gap** | `--space-lg` (24px) | `Astryx semantic token TBD — pending official Astryx package/docs confirmation` |
| **Card Padding** | `--space-md` (16px) | `Astryx semantic token TBD — pending official Astryx package/docs confirmation` |
| **Form Field Gap** | `--space-sm` (8px) | `Astryx semantic token TBD — pending official Astryx package/docs confirmation` |
| **Table Density** | Custom tight padding | `Astryx semantic token TBD — pending official Astryx package/docs confirmation` |
| **Drawer Padding** | `--space-md` (16px) | `Astryx semantic token TBD — pending official Astryx package/docs confirmation` |
| **Modal Padding** | `--space-lg` (24px) | `Astryx semantic token TBD — pending official Astryx package/docs confirmation` |
| **Card Radius** | `--radius-md` (8px) | `Astryx semantic token TBD — pending official Astryx package/docs confirmation` |
| **Button Radius** | `--radius-md` (8px) | `Astryx semantic token TBD — pending official Astryx package/docs confirmation` |
| **Input Radius** | `--radius-sm` (4px) | `Astryx semantic token TBD — pending official Astryx package/docs confirmation` |
| **Toast Radius** | `--radius-md` (8px) | `Astryx semantic token TBD — pending official Astryx package/docs confirmation` |
| **Modal/Drawer Radius** | `--radius-lg` (12px) | `Astryx semantic token TBD — pending official Astryx package/docs confirmation` |
| **Status: Draft** | `--status-draft` (yellow) | `Astryx semantic token TBD — pending official Astryx package/docs confirmation` |
| **Status: Warning** | `--status-warning` (orange) | `Astryx semantic token TBD — pending official Astryx package/docs confirmation` |
| **Status: Error** | `--status-error` (red) | `Astryx semantic token TBD — pending official Astryx package/docs confirmation` |
| **Status: Approved** | `--status-approved` (green) | `Astryx semantic token TBD — pending official Astryx package/docs confirmation` |
| **Status: Locked** | `--status-blocking` (dark red) | `Astryx semantic token TBD — pending official Astryx package/docs confirmation` |
| **Status: Synced** | `--status-approved` (green) | `Astryx semantic token TBD — pending official Astryx package/docs confirmation` |
| **Status: Unsaved** | `--status-warning` (orange) | `Astryx semantic token TBD — pending official Astryx package/docs confirmation` |
| **Status: Saved** | `--status-approved` (green) | `Astryx semantic token TBD — pending official Astryx package/docs confirmation` |
| **Feedback: Toast** | Custom Popup wrapper | `Astryx semantic token TBD — pending official Astryx package/docs confirmation` |
| **Feedback: Inline Alert** | `ApiErrorBanner.tsx` | `Astryx semantic token TBD — pending official Astryx package/docs confirmation` |
| **Feedback: Banner** | `RbacLockNotice.tsx` | `Astryx semantic token TBD — pending official Astryx package/docs confirmation` |
| **Feedback: Empty State** | `EmptyState.tsx` | `Astryx semantic token TBD — pending official Astryx package/docs confirmation` |
| **Feedback: Dialog** | `ConflictWarning.tsx` | `Astryx semantic token TBD — pending official Astryx package/docs confirmation` |

---

## 4. Component Mapping by MVP Screen

### 4.1 App Shell & Layout
| Screen Sub-unit | Custom React Component | Astryx Component Candidate Pattern |
| :--- | :--- | :--- |
| Navigation Sidebar | `.sidebar` | Astryx Navigation Sidebar pattern — exact component name TBD |
| Page Header / Title | `.workbench-header` | Astryx Page Header pattern — exact component name TBD |
| Breadcrumb navigation | Custom elements | Astryx Breadcrumb pattern — exact component name TBD |
| User Profile Menu | Custom elements | Astryx Dropdown Menu / User Menu pattern — exact component name TBD |
| App Status Indicator | Custom connection logs | Astryx Status Badge pattern — exact component name TBD |

### 4.2 Project List (Hồ sơ)
| Screen Sub-unit | Custom React Component | Astryx Component Candidate Pattern |
| :--- | :--- | :--- |
| Project Table | Custom tables | Astryx Data Table pattern — exact component name TBD |
| Search bar & Filter dropdowns | Custom HTML buttons | Astryx Search Input, Select pattern — exact component name TBD |
| Status Chips | `.badge` | Astryx Tag / Badge pattern — exact component name TBD |
| Empty State | `EmptyState.tsx` | Astryx Empty State pattern — exact component name TBD |

### 4.3 Excel Import Flow
| Screen Sub-unit | Custom React Component | Astryx Component Candidate Pattern |
| :--- | :--- | :--- |
| Upload Dropzone | HTML input element | Astryx File Upload/Dropzone pattern — exact component name TBD |
| Stepper Progress | Custom flow indicators | Astryx Stepper pattern — exact component name TBD |
| Column Mapping Preview | Custom mapping table | Astryx Interactive Table pattern — exact component name TBD |
| Import Validation Summary| Custom error components | Astryx Alert pattern — exact component name TBD |

### 4.4 Validation Dashboard (Bảng lỗi cần xử lý)
| Screen Sub-unit | Custom React Component | Astryx Component Candidate Pattern |
| :--- | :--- | :--- |
| Error summary cards | Custom `.panel-tab` | Astryx Card pattern — exact component name TBD |
| Filter tabs | Custom navigation items | Astryx Tabs pattern — exact component name TBD |
| Data issue list | Custom validation items | Astryx Data List/Table pattern — exact component name TBD |
| Row-level action buttons | Custom table cells action links | Astryx Button / Icon Button pattern — exact component name TBD |
| Guidance helper panel | Custom side-panel widgets | Astryx Info Banner pattern / "Tôi cần làm gì tiếp?" helper panel — exact component name TBD |

### 4.5 Live Workbench (Bàn làm việc hồ sơ)
| Screen Sub-unit | Custom React Component | Astryx Component Candidate Pattern |
| :--- | :--- | :--- |
| Asset Grid Table | Virtualized asset grid | Astryx Data Table/Grid pattern (with inline editing cell locks) — exact component name TBD |
| Draft state indicator | Custom cell marker | Astryx Status Indicator / Tag pattern — exact component name TBD |
| Row status chips | Status badges | Astryx Tag / Badge pattern — exact component name TBD |
| Context drawer | Context Drawer widget | Astryx Drawer/Side Panel pattern — exact component name TBD |
| Right-side assistant panel | Assistant drawer panel | Astryx Drawer/Side Panel pattern — exact component name TBD |
| Save draft button | Action trigger | Astryx Button pattern — exact component name TBD |
| Submit review button | Action trigger | Astryx Button pattern — exact component name TBD |
| Conflict warning | `ConflictWarning.tsx` | Astryx Dialog/Modal pattern (optimistic locking conflicts) — exact component name TBD |
| Unsaved changes warning | Custom leave popup | Astryx Modal/Dialog pattern — exact component name TBD |
| Action buttons | `.action-btn` | Astryx Button pattern — exact component name TBD |

### 4.6 Asset Context Drawer
| Screen Sub-unit | Custom React Component | Astryx Component Candidate Pattern |
| :--- | :--- | :--- |
| Main Context Drawer | `.workbench-right-drawer` | Astryx Drawer/Side Panel pattern (Right-side alignment) — exact component name TBD |
| Metadata card | Detailed field forms | Astryx Card / Form pattern — exact component name TBD |
| Evidence list / Price cards | Custom cards | Astryx Card List pattern — exact component name TBD |
| Similar asset references | Reference cards link list | Astryx Link List / Card pattern — exact component name TBD |
| History/audit timeline | Custom timeline | Astryx Timeline pattern — exact component name TBD |

### 4.7 Trợ lý Valora (AI Assistant)
| Screen Sub-unit | Custom React Component | Astryx Component Candidate Pattern |
| :--- | :--- | :--- |
| Assistant Drawer panel | Custom tabs | Astryx Drawer/Side Panel pattern — exact component name TBD |
| Suggestion Card | Custom card markup | Astryx Interactive Card pattern (Accept/Reject actions) — exact component name TBD |

### 4.8 Review / Approval Flow
| Screen Sub-unit | Custom React Component | Astryx Component Candidate Pattern |
| :--- | :--- | :--- |
| Review queue | Table list of pending reviews | Astryx Data Table pattern — exact component name TBD |
| Diff Comparison | Custom table cells diffs | Astryx Diff Viewer pattern — exact component name TBD |
| Approval checklist | Custom selection checks | Astryx Checklist/Checkbox pattern — exact component name TBD |
| Return for correction modal | Reject feedback overlay | Astryx Dialog/Modal pattern — exact component name TBD |
| Approval Dialog | Custom alert modal | Astryx Dialog/Modal pattern — exact component name TBD |

### 4.9 Draft Report Generation
| Screen Sub-unit | Custom React Component | Astryx Component Candidate Pattern |
| :--- | :--- | :--- |
| Report template selector | Select inputs | Astryx Select / Dropdown pattern — exact component name TBD |
| Data readiness checklist | Validation list | Astryx Checklist pattern — exact component name TBD |
| Generate draft report button | Action trigger | Astryx Button pattern — exact component name TBD |
| Export status | Generation spinner | Astryx Progress Bar / Spinner pattern — exact component name TBD |
| Download result | Custom file links | Astryx Link / Button pattern — exact component name TBD |
| Failure recovery message | Inline warnings banner | Astryx Alert / Banner pattern — exact component name TBD |

### 4.10 Auth / User Management
| Screen Sub-unit | Custom React Component | Astryx Component Candidate Pattern |
| :--- | :--- | :--- |
| Login Form | Form controls markup | Astryx Form / Text Input pattern — exact component name TBD |
| Role labels | Badges | Astryx Badge/Tag pattern — exact component name TBD |
| Permission errors | `RbacLockNotice.tsx` | Astryx Banner pattern — exact component name TBD |
| Session expired message | Session overlay block | Astryx Modal/Dialog pattern — exact component name TBD |

---

## 5. Vietnamese Label Mapping

Core labels utilized inside the localized i18n dictionaries:

| Vietnamese Label | Usage Context |
| :--- | :--- |
| Bàn làm việc hồ sơ | Workbench page main heading |
| Danh sách hồ sơ | Project grid lists heading |
| Nhập dữ liệu | Ingest button / Upload step |
| Kiểm tra dữ liệu | Data verification runner |
| Bảng lỗi cần xử lý | Validation dashboard label |
| Bổ sung giá/thông tin | Step description for asset line edits |
| Lưu nháp | Manual autosave draft checkpoint trigger |
| Đã lưu nháp | Status tag for draft synced states |
| Chưa lưu | Status tag indicating pending modifications |
| Khôi phục bản nháp | Retrieve draft changes trigger |
| Gửi duyệt | Submit to reviewer QC trigger |
| Trả về chỉnh sửa | Send back to appraiser command |
| Đã duyệt | Approved status indicator |
| Xuất báo cáo nháp | Create draft report compiler trigger |
| Trợ lý Valora | Main header title for the AI side drawer |
| Gợi ý | Title text for card-based AI recommendations |
| Chấp nhận | Apply suggestion button label |
| Từ chối | Dismiss recommendation button label |
| Có lỗi cần xử lý | Alert banner warning state header |
| Mất kết nối máy chủ | Local connection failure label |
| Dữ liệu đã được người khác cập nhật | Optimistic locking conflict dialog header |
| Tài khoản chưa có quyền thực hiện thao tác này | Permission block description |

---

## 6. Non-IT Error Translation Map

All HTTP failures must map to friendly Vietnamese dialog representations:

| Technical Failure Case | User-facing Vietnamese Translation | Actionable Guidance |
| :--- | :--- | :--- |
| **Network Failure** | Không thể kết nối với máy chủ | Vui lòng kiểm tra lại đường truyền mạng hoặc liên hệ quản trị viên để hỗ trợ. |
| **401 Unauthenticated** | Phiên làm việc đã hết hạn | Vui lòng đăng nhập lại để tiếp tục bàn làm việc. |
| **403 Forbidden** | Tài khoản chưa được cấp quyền thực hiện thao tác này | Bạn cần liên hệ Quản trị viên để đăng ký vai trò phù hợp. |
| **409 Conflict** | Dữ liệu hồ sơ này đã được thay đổi bởi người dùng khác | Vui lòng bấm "Cập nhật mới" để đồng bộ dữ liệu mới nhất trước khi chỉnh sửa. |
| **422 Validation Error** | Thông tin nhập vào chưa đúng định dạng | Vui lòng kiểm tra lại các trường được đánh dấu đỏ trên màn hình. |
| **500 Server Error** | Hệ thống gặp lỗi xử lý nội bộ | Thao tác không thành công. Vui lòng thử lại sau vài phút. |
| **AI provider timeout** | Trợ lý Valora phản hồi chậm | Tiến trình phân tích đang bận. Vui lòng thử lại sau. |
| **AI provider unavailable**| Trợ lý Valora tạm thời không khả dụng | Tính năng gợi ý thông minh đang tạm bảo trì. Bạn vẫn có thể nhập giá thủ công. |
| **Excel parse error** | Tệp Excel tải lên không hợp lệ | Đọc tệp thất bại. Vui lòng kiểm tra lại các cột dữ liệu theo tệp mẫu. |
| **Unsupported format** | Định dạng tệp không được hỗ trợ | Vui lòng chỉ tải lên các tệp có đuôi mở rộng `.xlsx` hoặc `.xls`. |
| **Unsaved changes warning**| Bạn có các thay đổi chưa được lưu | Bấm "Quay lại" để lưu nháp, hoặc "Rời đi" để hủy bỏ các thay đổi này. |
| **Lost connection save** | Lưu nháp thất bại do mất kết nối | Bản nháp của bạn đã được sao lưu tạm thời trên trình duyệt. Hệ thống sẽ tự động gửi lại khi có mạng. |

---

## 7. Implementation Rules for Future PRs
- **Token Compliance**: Frontend stylesheets must only inherit Astryx tokens. Direct hex color values or hardcoded margins/paddings are forbidden.
- **Strict Verification Blockers**: 
  - Any raw JSON error log, backend stack trace, or HTTP code exposed to the UI.
  - Any direct mention of AI model provider names (e.g. Gemini, DeepSeek) inside client screens (must use *Trợ lý Valora*).
  - Any user-facing label defined in English.

---

## 8. Proposed Migration Plan
1. **S10-PR-003**: Create localized `i18n` translations files setup.
2. **S10-PR-004**: Build standard error translation utility wrappers masking HTTP status exceptions.
3. **S10-PR-005**: Re-align the basic React App Shell layouts to inherit standard Astryx container structures.
4. **S11+**: Inject mappings systematically across the Asset Grid, Excel Ingest forms, and AI drawer panels.

---

## 9. Acceptance Criteria

S10-PR-002 passes when:
- Current frontend UI inventory is documented.
- Astryx library status (Not Installed) and the transition mapping plan are documented.
- Astryx token mappings are declared with placeholder flags where exact package imports are pending.
- Component mapping mappings exist for all MVP screen widgets.
- Vietnamese labels dictionaries are declared.
- Non-IT UX translated errors are cataloged.
- Future implementation check rules are clear.
- No runtime code is modified.
- Existing tests compile and run without error.
