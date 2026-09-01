# VALORA UI/UX v2.3 — Microsoft 365 Return / Revalidation Contract v1

**Status:** Baseline / Design Authority  
**Contract:** v1  
**Date:** 01/09/2026  
**Scope:** Microsoft 365 Document Workspace — return from external Word/Microsoft 365 editing, revalidation, stale/conflict classification, and safe continuation into sync/publishing.

## 1. Purpose

Contract này khóa hành vi khi người dùng mở tài liệu từ VALORA sang Microsoft Word/Microsoft 365 rồi quay lại VALORA. Mục tiêu là đảm bảo VALORA không giả định file không đổi, không silent overwrite, không tạo revision giả, và không cho Sync/Publishing tiếp tục trên trạng thái M365 chưa được xác minh khi freshness là bắt buộc.

Return/Revalidation là integration/state contract, **không phải workflow checkpoint mới**.

## 2. Authority boundary

- VALORA sở hữu structured business data, Data Snapshot, lineage, audit, sync status, Document Revision và Release Manifest.
- Microsoft 365 sở hữu Word file, OneDrive/SharePoint file và M365 file version.
- `Document Revision != Microsoft 365 file version`.
- Word là nơi chỉnh sửa tài liệu; VALORA không xây fake Word editor.
- Revalidation chỉ xác minh và phân loại trạng thái. Nó không tự commit business decision, không tự tạo Document Revision, không tự publish.

## 3. Canonical mental flow

```text
Mở trong Word
→ VALORA ghi nhận handoff context
→ user quay lại / workspace regain focus / explicit refresh / action cần freshness
→ BACKGROUND_REFRESH: revalidate M365 file state
→ so sánh với M365 file/version đã bind vào Document Revision hiện hành
→ phân loại return state
→ derive document sync/readiness state
→ tiếp tục bình thường hoặc yêu cầu review/conflict/recovery
```

Không coi việc user quay lại VALORA là bằng chứng Word đã thay đổi.

## 4. Handoff context

Khi `Mở trong Word`, VALORA có thể ghi nhận context phục vụ revalidation tối thiểu:

```text
project_id
document_id
document_revision_id
m365_file_id / drive_item_id nếu có
m365_version_reference đã biết
managed_region baseline / snapshot reference
opened_at
```

Handoff context là technical/integration context, không phải business commit và không làm tăng completion.

## 5. Revalidation triggers

Revalidation được kích hoạt khi có một trong các điều kiện phù hợp:

1. Workspace/document view regain focus sau external editing handoff.
2. User explicit `Làm mới` / `Kiểm tra thay đổi`.
3. Trước thao tác cần freshness như Sync, review sync readiness hoặc Publishing readiness khi trạng thái M365 hiện tại chưa được xác minh theo policy.
4. Reconnect sau offline/session interruption.
5. M365 webhook/change notification có thể đánh dấu stale và yêu cầu revalidation, nhưng notification không tự được coi là nội dung cuối cùng đã xác minh.

Không poll vô hạn chỉ để giữ màn hình ở trạng thái loading.

## 6. Presentation state during revalidation

Revalidation ban đầu dùng cross-product state `BACKGROUND_REFRESH` khi đã có usable data:

- giữ nguyên tài liệu/metadata đang xem;
- hiển thị trạng thái nhẹ như `Đang kiểm tra thay đổi từ Word…`;
- không blank page;
- không disable toàn bộ workspace nếu chỉ một document đang refresh;
- official mutation phụ thuộc freshness có thể tạm disable hoặc yêu cầu hoàn tất revalidation.

Nếu chưa có usable data, áp dụng Initial/Section Loading theo Cross-product State Contract.

## 7. Canonical return classification

Revalidation phải derive một trong các semantic result sau:

### 7.1 `NO_CHANGE`
M365 file/version/content relevant không thay đổi so với baseline đã bind.

Kết quả: giữ current state; không tạo Document Revision mới.

### 7.2 `EXTERNAL_CHANGE_OUTSIDE_MANAGED`
Có thay đổi Word/M365 nhưng chỉ nằm ngoài Managed Regions do VALORA sở hữu.

Kết quả: ghi nhận M365 file/version mới và trạng thái user-edited phù hợp; không mặc định tạo sync conflict. Narrative ngoài Managed Regions được bảo toàn.

### 7.3 `EXTERNAL_CHANGE_IN_MANAGED`
Một hoặc nhiều Managed Regions đã bị thay đổi trong Word so với baseline đã bind.

Kết quả: đánh dấu vùng cần revalidation/review. Không silent overwrite.

Nếu đồng thời dữ liệu VALORA của cùng Managed Region cũng thay đổi so với snapshot cũ, đây là candidate cho Sync Conflict và phải đi theo Conflict Resolution baseline.

Nếu VALORA data không đổi nhưng Word thay đổi trong Managed Region, không gọi đó là three-way conflict giả; hệ thống phải giữ current Word content và yêu cầu xử lý phù hợp trước lần sync có nguy cơ overwrite.

### 7.4 `FILE_REPLACED_OR_MOVED`
File identity/path/binding không còn khớp hoặc file đã được thay thế/di chuyển theo cách làm mất binding đáng tin cậy.

Kết quả: `STALE_DATA` hoặc blocking integration condition tùy khả năng resolve. Không tự bind file khác chỉ vì tên giống nhau.

### 7.5 `ACCESS_UNAVAILABLE`
Không thể xác minh M365 state do permission/session/network/provider error.

Kết quả: giữ usable data cũ nếu có, hiển thị trạng thái chưa xác minh + recovery action. Không giả `Đã đồng bộ`, `Sẵn sàng phát hành` hay success mới.

## 8. Comparison baseline

Nguồn so sánh chuẩn là M365 file/version reference và Managed Region state đã bind vào **Document Revision hiện hành / lần sync thành công gần nhất có lineage hợp lệ**.

Không dùng:
- thời điểm mở màn hình;
- filename đơn thuần;
- last visited route;
- local UI cache không có lineage
làm source of truth cho revalidation.

## 9. Managed Region change rules

Đối với từng Managed Region:

```text
Old = giá trị tại snapshot/lần sync đã bind
V = dữ liệu VALORA hiện tại
W = nội dung Word hiện tại sau revalidation
```

Semantic rules:

- `V = Old` và `W = Old` → không đổi.
- `V = Old` và `W != Old` → Word-only edit; bảo toàn W, không silent overwrite.
- `V != Old` và `W = Old` → VALORA-only change; vùng `Cần cập nhật`, không conflict.
- `V != Old` và `W != Old` → nếu V và W khác nhau theo comparison semantics của region thì conflict cần explicit decision.
- Nếu V và W hội tụ về cùng semantic value, implementation có thể classify non-conflict nhưng phải giữ audit/lineage đủ để giải thích.

Comparison semantics phải phù hợp loại Managed Region; không dùng raw string equality cho mọi kiểu dữ liệu nếu domain đã có normalization authority.

## 10. Document Revision and M365 version semantics

- Phát hiện M365 version mới **không tự tạo Document Revision**.
- Revalidation không silent mutate published Document Revision.
- Document Revision mới chỉ được tạo tại write boundary đã được authority cho phép, ví dụ sync/generation/version command thành công.
- M365 version có thể thay đổi do user edit ngoài VALORA và vẫn phải được lineage ghi nhận mà không giả thành VALORA Document Revision mới.
- Published revision/release immutable.

## 11. Safe continuation gates

### Sync
Trước `Xác nhận & Đồng bộ`, Managed Regions trong scope phải có freshness đủ theo sync policy. Nếu phát hiện conflict thì phải resolve theo `Xử lý xung đột khi đồng bộ` trước write boundary.

### Publishing
Publishing readiness không được dựa trên M365 state đã biết là stale/chưa xác minh nếu tài liệu đó yêu cầu freshness. Một integration freshness failure có thể trở thành Blocking khi nó làm hệ thống không thể chứng minh revision/file binding đủ điều kiện phát hành.

Warning vẫn không tự biến thành Blocking; Blocking chỉ phát sinh khi business/integrity rule thật sự ngăn commit.

### Global Case State
Kết quả revalidation phải feed vào document/release readiness facts để Global Case State derive `stale`, `blocking`, `next_action` và resume context. Frontend không tự dựng workflow truth riêng.

## 12. Failure and recovery

- Read/revalidation failure: giữ usable old data + stale/error indicator + `Thử lại` đúng scope.
- Offline: không fake success; khi reconnect phải revalidate trước official mutation phụ thuộc freshness.
- Auth/session expired: yêu cầu reconnect/sign-in theo integration pattern; không biến thành `Không có dữ liệu`.
- 409/version conflict ở VALORA: reload/reconcile/review rồi explicit commit lại; không last-write-wins.
- Provider timeout không đồng nghĩa file không thay đổi.

## 13. Audit and lineage

Revalidation phải audit/trace đủ để giải thích tối thiểu:

```text
Document
→ Document Revision baseline
→ M365 file/version baseline
→ revalidation trigger/time
→ observed M365 file/version
→ affected Managed Regions nếu xác định được
→ semantic classification
→ downstream review/conflict/sync action nếu có
```

Không cần biến mọi background refresh thành noisy business activity; implementation có thể tách technical telemetry và durable audit. Nhưng mọi state ảnh hưởng Sync/Publishing eligibility phải truy vết được.

## 14. UX language authority

Ưu tiên nhãn nghiệp vụ:

- `Đang kiểm tra thay đổi từ Word…`
- `Không có thay đổi mới`
- `Có thay đổi trong Word`
- `Có nội dung cần xem lại trước khi đồng bộ`
- `Chưa thể kiểm tra phiên bản Word hiện tại`
- `Kiểm tra lại`
- `Mở trong Word`
- `Xem thay đổi`

Không dùng raw enum/code làm primary copy.

## 15. Hard invariants

1. Quay lại VALORA không đồng nghĩa Word đã thay đổi.
2. Revalidation không phải business commit.
3. Revalidation không tạo workflow checkpoint mới.
4. Có usable data thì revalidation dùng background refresh, không blank page.
5. M365 version mới không tự tạo Document Revision.
6. Thay đổi ngoài Managed Region không mặc định là sync conflict.
7. Managed Region user-edited không bị silent overwrite.
8. Three-way conflict chỉ khi các điều kiện conflict thật sự thỏa mãn.
9. Không tự bind file thay thế chỉ dựa vào filename.
10. Không fake `Đã đồng bộ`/`Sẵn sàng phát hành` khi freshness chưa xác minh.
11. Published revision/release immutable.
12. Reconnect phải refresh/revalidate trước mutation phụ thuộc freshness.
13. Frontend không duy trì M365/document workflow truth độc lập với backend projection/domain facts.
14. Một primary recovery CTA mỗi error/revalidation context.
15. Không Export PDF; không fake Word editor.

## 16. Relationship to existing authority

Contract này kế thừa và nối:

```text
Microsoft 365 Document Workspace
→ Microsoft 365 Return / Revalidation Contract v1
→ Document Sync & Version
→ Conflict Resolution khi cần
→ Global Case State / Publishing readiness
```

Nó không supersede layout/flow của Document Sync, Conflict Resolution, Publishing hoặc Cross-product State Contract ngoài phần return/revalidation được quy định rõ tại đây.

## 17. Implementation / ADR boundary

Đây là Design Authority contract, không đồng nghĩa product code đã implement.

Nếu implementation bổ sung/thay đổi:
- Microsoft Graph/OneDrive/SharePoint integration persistence;
- webhook/change notification semantics;
- M365 file identity/version binding;
- Managed Region content fingerprint/diff storage;
- freshness TTL/policy;
- revalidation audit persistence;
- document readiness projection;
- transaction/concurrency semantics;

thì phải đánh giá ADR kỹ thuật trước khi thay đổi persistence/architecture.

## 18. Visual authority

Contract v1 được chốt trước visual. Mockup/pattern `M365 Return & Revalidation` sau này mặc định là Design Proposal / Iteration cho đến khi người dùng explicit nâng thành Baseline. Contract này là semantic authority ngay từ thời điểm chốt.