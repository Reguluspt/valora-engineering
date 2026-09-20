# VALORA UI/UX v2.3 — Working Change Observation / Change Candidate / Human Commit — Baseline Addendum

**Status:** Baseline / Design Authority  
**Contract:** v1  
**Date:** 21/09/2026  
**Scope:** Document Workspace — Working-copy change observation, automatic revalidation, change analysis, review/conflict and authoritative Document Revision commit.

## 1. Quyết định baseline

Product Owner chốt mental model mới cho tài liệu Word làm việc qua Microsoft 365:

> VALORA được phép tự động phát hiện, đọc, phân tích và đề xuất xử lý thay đổi từ Working copy; nhưng không được tự động thay đổi business truth hoặc tạo Document Revision mới.

Đây là semantic authority mới hơn cho phần Working-copy re-import/review. Addendum này mở rộng:
- `Microsoft 365 Return / Revalidation Contract v1`;
- `Document Sync & Version`;
- `Sync Conflict Resolution`;
- ADR 0043/0044.

Nếu wording/flow cũ hiểu `Nhập thay đổi` là immediate promotion thành `DocumentRevision N+1`, contract này thắng trong đúng scope đó.

Không tạo canonical workflow stage thứ 17.

## 2. Canonical meaning của Document Revision

`DocumentRevision` là một phiên bản tài liệu nghiệp vụ mà VALORA đã **chính thức chấp nhận**.

Không đồng nhất:
- Word Save;
- Microsoft 365 file version;
- provider change notification;
- checksum khác;
- revalidation observation;
- Change Candidate

với Document Revision.

Canonical invariant:

```text
Document Revision != Microsoft 365 file version
Word Save != VALORA business commit
Provider change != accepted authoritative revision
```

`DocumentRecord` giữ identity ổn định; các `DocumentRevision` append-only; `DocumentRevisionCurrentHead` chỉ trỏ tới revision đã được VALORA chấp nhận.

## 3. Canonical mental flow

```text
VALORA Revision N
→ tạo Working copy
→ user chỉnh sửa + Save trong Word
→ provider change được quan sát / workspace regain focus / action cần freshness
→ AUTO REVALIDATION
→ xác minh đúng provider item + version/content
→ đọc DOCX có kiểm soát khi cần
→ Managed Region diff
→ so sánh Old / V / W
→ tạo Change Candidate
→ rule/AI có thể đưa đề xuất
→ user xem & xác nhận
→ domain command / accepted document-version plan
→ Revision N+1
```

Trong đó:
- `Old` = giá trị bind vào accepted revision/lần sync baseline gần nhất;
- `V` = authoritative VALORA business value hiện tại;
- `W` = giá trị Word hiện tại sau verified revalidation.

## 4. Trigger authority

VALORA ưu tiên tự động quan sát thay đổi, không bắt user thực hiện manual import chỉ để hệ thống biết Word đã đổi.

Trigger hợp lệ:
1. Microsoft Graph change notification cho Working folder/hierarchy.
2. Workspace regain focus sau external editing handoff.
3. Mở lại Document Workspace/document.
4. Explicit `Kiểm tra thay đổi`.
5. Trước Sync/Revision/Publishing action cần freshness.
6. Reconnect sau offline/provider interruption.

Change notification chỉ đánh dấu `potentially changed / stale`; không phải bằng chứng nội dung cuối cùng.

## 5. Automatic processing boundary — read-only đối với authority

Automatic processing được phép:
- nhận notification và đánh dấu Working copy stale;
- chạy delta/exact-item revalidation;
- kiểm tra provider identity/version/tag;
- tải bounded DOCX content khi cần;
- kiểm tra SHA-256/byte length;
- fingerprint/diff Managed Regions;
- so sánh `Old / V / W`;
- tạo non-authoritative Change Candidate;
- sinh warning/conflict/recommendation;
- chạy deterministic rule hoặc AI advisory analysis.

Automatic processing không được:
- mutate authoritative business data;
- accept Word value vào domain truth;
- resolve conflict;
- tạo `DocumentRevision N+1`;
- advance `DocumentRevisionCurrentHead`;
- publish/release.

## 6. Change Candidate semantics

Change Candidate là review artifact, không phải business truth và không phải Document Revision.

Candidate phải trace được tối thiểu:
- Project/Document;
- baseline `DocumentRevision`;
- Working provider item identity;
- observed provider version/tags;
- content/fingerprint evidence;
- affected Managed Regions;
- `Old / V / W` comparison;
- classification;
- generated recommendation;
- review/decision lineage khi có.

Candidate có thể bị stale/superseded nếu Working file, VALORA data hoặc baseline revision thay đổi trước commit.

Không được dùng candidate cũ để blind commit.

## 7. Canonical classification

### 7.1 No change

```text
Old = V = W
```

- không tạo revision;
- CurrentHead giữ nguyên.

### 7.2 Chỉ thay đổi ngoài Managed Regions

Business-managed data không đổi; narrative/user-editable Word content đổi.

- bảo toàn narrative Word;
- hiển thị diff;
- user explicit xác nhận nếu muốn ghi nhận phiên bản tài liệu mới;
- chỉ sau confirmation mới tạo `Revision N+1`.

### 7.3 Word-only change trong Managed Region

```text
Old = V
W != Old
```

Không gọi đây là three-way conflict giả.

- giữ Word observation trong candidate;
- hiển thị VALORA value và Word value;
- yêu cầu explicit handling trước operation có nguy cơ overwrite.

Nếu Managed Region đại diện authoritative business truth, preferred semantics:

```text
Word change
→ đề xuất cập nhật domain data
→ user xác nhận domain command
→ business truth mới
→ accepted document revision
```

Word là proposal source, không phải source of truth.

### 7.4 VALORA-only change

```text
V != Old
W = Old
```

- vùng `Cần cập nhật`;
- không conflict;
- user review/update plan trước write boundary.

### 7.5 True three-way conflict

```text
V != Old
W != Old
V != W
```

- vào Conflict Review;
- hiển thị `Old | VALORA | Word`;
- explicit decision từng region;
- conflict decision vẫn zero-write đối với Document Revision;
- final accepted plan + user confirmation mới được tạo revision.

Nếu V và W hội tụ cùng semantic value, implementation có thể classify non-conflict nếu audit/lineage đủ.

## 8. UX authority

Khi automatic observation/revalidation phát hiện thay đổi, ưu tiên:

```text
Đã phát hiện thay đổi từ Word
→ Xem & xác nhận thay đổi
```

Fallback khi automatic observation không khả dụng:

```text
Kiểm tra thay đổi
```

Không dùng primary mental model:
```text
Nhập thay đổi
→ tạo phiên bản ngay
```

`Nhập thay đổi` nếu còn xuất hiện phải có nghĩa là bắt đầu kiểm tra/đưa thay đổi vào review pipeline, không phải authoritative commit.

Preferred user-facing name của canonical `DOCUMENT_SYNC_REVIEW`:
- `Rà soát thay đổi tài liệu`; hoặc
- `Xem lại thay đổi & tạo phiên bản mới`.

Backend enum có thể giữ nguyên để bảo toàn compatibility.

## 9. Revision creation boundary

Cho phép tạo `DocumentRevision` tại các business write boundary được authority cho phép, ví dụ:
1. initial DOCX import accepted vào VALORA;
2. successful VALORA generation/version command;
3. accepted Working-copy change sau review/conflict;
4. successful managed-region document update;
5. future explicitly authorized version command.

Không tạo revision chỉ vì:
- Word Save;
- provider notification;
- Microsoft 365 version mới;
- return/focus;
- revalidation;
- preview;
- candidate creation;
- draft conflict decision;
- Working-copy creation;
- Export creation.

## 10. Observation reliability

Working Change Observation là convenience/near-real-time layer, không phải correctness authority.

Dùng mô hình ba lớp:

```text
PRIMARY
Graph change notification
→ đánh dấu potentially changed

FALLBACK
focus/open/explicit check
→ revalidate/delta

SAFETY GATE
trước Revision / Sync / Publishing
→ exact freshness/revalidation bắt buộc
```

Mất webhook không được làm correctness phụ thuộc vào notification delivery.

## 11. AI/rule authority

Rule/AI được phép:
- tóm tắt diff;
- phân loại candidate;
- đề xuất giữ Word / dùng VALORA / yêu cầu review;
- giải thích lý do và evidence.

Rule/AI không được:
- tự xác nhận Word value thành business truth;
- tự resolve conflict;
- tự tạo revision;
- giả danh human approval.

## 12. Global Case State

Working Change Observation không tạo stage thứ 17.

Nó feed vào:
- `DOCUMENT_WORKSPACE` readiness/freshness;
- `DOCUMENT_SYNC_REVIEW` stale/blocking/review facts;
- Publishing readiness khi document freshness là bắt buộc.

Frontend không dựng workflow truth riêng.

## 13. Audit / Lineage

Trace tối thiểu:

```text
Document
→ accepted Document Revision baseline
→ Working provider item/version
→ observation trigger/time
→ revalidation evidence
→ Change Candidate
→ Old / V / W + affected Managed Regions
→ recommendation
→ human/domain decision
→ accepted Revision N+1 (nếu có)
```

Technical notifications có thể là telemetry; mọi observation/candidate/decision ảnh hưởng eligibility hoặc revision commit phải truy vết được.

## 14. Relationship với G8

G8 storage/Exchange machinery được giữ lại:
- immutable blob;
- CurrentHead CAS;
- `NEXT_REVISION`;
- idempotency;
- provider-unknown recovery;
- late-collision protection;
- capability ledger;
- create-new-only Working/Export;
- XLSX staging isolation.

Target orchestration đổi từ:

```text
Nhập thay đổi
→ verify
→ NEXT_REVISION
```

thành:

```text
provider change / return
→ auto revalidate
→ verify
→ Change Candidate
→ Old / V / W
→ review / recommendation / conflict
→ human confirmation
→ approved revision command
→ NEXT_REVISION
```

Không rewrite storage engine.

## 15. Hard invariants

1. OneDrive/Microsoft 365 không phải business source of truth.
2. Notification không phải authoritative evidence.
3. Auto revalidation không phải business commit.
4. Change Candidate không phải Document Revision.
5. Word Save không tạo Revision.
6. User-edited Managed Region không silent overwrite.
7. True conflict cần explicit human decision.
8. Candidate stale phải re-review.
9. Published revision/release immutable.
10. Safety revalidation bắt buộc trước official mutation phụ thuộc freshness.
11. AI advisory only.
12. Một primary review/commit CTA mỗi context.

## 16. ADR / implementation boundary

Persistence hoặc runtime cho:
- Graph subscription lifecycle;
- webhook validation/delivery;
- delta cursor;
- Working change observation;
- Change Candidate;
- managed-region diff;
- freshness/stale policy;
- background job/idempotency;
- human-confirmed revision command

phải tuân ADR 0045.

Exact schema/API/job contract cần task-specific implementation contract trước runtime.
