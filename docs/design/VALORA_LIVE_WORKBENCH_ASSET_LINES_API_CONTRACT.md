# Live Workbench Project Asset Lines API Contract

- **Status**: Authoritative API Contract
- **Sprint Target**: S11-PR-001

---

## 1. Purpose
This document establishes the backend-to-frontend schema and route structure for loading project asset lines into the Live Workbench.

## 2. Relationship to Authoritative Contracts
- **Relationship to Design Book v1.3**: Strictly implements the closed-loop data loop, ensuring that all variables displayed in client layouts exclude backend transaction details or SQL errors, and AI indicators are styled as "Trợ lý Valora".
- **Relationship to Vietnamese i18n Dictionary**: Keys like status values mapping to `needs_review` or `draft` are externalized and translated into Vietnamese business terms (`Bản nháp`, `Chờ kiểm tra`) inside client templates.
- **Relationship to Non-IT Error Message Registry**: Mapped exception classes (401, 403, 404) trigger localized, actionable friendly messages.

## 3. API Route Structure

- **Endpoint**: `GET /api/v1/projects/{project_id}/asset-lines`
- **Route Namespace**: Projects Domain (`/api/v1/projects`)
- **Required Permission**: `project:read` (Existing stable permission used to avoid introducing a new permission in S11-PR-001)

## 4. Query Parameters

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| **limit** | `int` | `50` | Maximum number of records to return (bounds: 1-100). |
| **offset** | `int` | `0` | Number of records to skip for pagination. |
| **search** | `str` | `None` | Case-insensitive filter matching asset names or descriptions. |
| **validation_status** | `str` | `None` | Filter by data quality status (`valid`, `invalid`, `needs_review`, `unvalidated`). |
| **valuation_status** | `str` | `None` | Filter by valuation review status (`draft`, `approved`, `returned`). |

## 5. Response Schema (JSON Pagination Wrapper)

```json
{
  "project_id": "uuid-string",
  "items": [
    {
      "id": "uuid-string",
      "project_id": "uuid-string",
      "asset_name": "string",
      "description": "string | null",
      "quantity": 1.0,
      "unit_id": "uuid-string | null",
      "raw_price": 1000000.0,
      "raw_price_currency_id": "uuid-string | null",
      "appraised_unit_price": 950000.0,
      "appraised_currency_id": "uuid-string | null",
      "review_status": "string (draft/approved/returned)",
      "validation_status": "string (unvalidated/valid/invalid/needs_review)",
      "brand_id": "uuid-string | null",
      "manufacturer_id": "uuid-string | null",
      "version_token": "string"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

### 5.1 Opaque Version Token Rule
- The `version_token` string acts as an opaque concurrency control token (mapped internally from the ORM's `row_version`).
- **Strict UI Guardrail**: This raw string token must never be displayed directly to non-IT end-users. It is processed silently by the client to support optimistic locking.

## 6. Route Scoping & Error Behavior
- **Multi-Tenant / Scoping**: The API checks that the project belongs to the user's active organization ID (`organization_id`). Accessing a project belonging to another organization yields a `404 Not Found` response to prevent ID harvesting.
- **Unauthorized**: Requests missing the authentication headers return `401 Unauthorized`.
- **Forbidden**: Users lacking the permission `project:read` return `403 Forbidden`.
- **Empty States**: If a project contains no asset lines, the API returns a `200 OK` status with the empty items wrapper structure:
```json
{
  "project_id": "project-uuid",
  "items": [],
  "total": 0,
  "limit": 50,
  "offset": 0
}
```

## 7. Frontend Client Integration
- TypeScript declarations and the fetch helper function reside in [assetLines.ts](file:///e:/Project%20Valora/valora-engineering-phase-sprint-0-starter/frontend/src/api/assetLines.ts).

## 8. Progressive Adoption Plan
- **S11-PR-001**: API Contract and Backend Endpoint (this PR).
- **S11-PR-002**: Workbench Asset Grid Read Adapter (binds real data to the grid).
- **S11-PR-003**: Context Drawer Data Adapter.
- **S11-PR-004**: Draft State Read Model.
- **S11-PR-005**: Inline Draft Editing Contract.
- **S11-PR-006**: Human Commit / Review Gate.
