# PR-07 — Implementation plan cho OAuth diagnostics và C2 research probe

> **For agentic workers:** Sau khi có approval local, dùng `superpowers:executing-plans` để thực hiện task-by-task với một implementation owner và reviewer độc lập. `superpowers:subagent-driven-development` chỉ phù hợp nếu vẫn giữ exclusive ownership của ba tools. Checklist chưa tick là việc chưa thực hiện; hướng dẫn execution không cấp authority vượt §1.

**Goal:** Chuẩn bị OAuth diagnostics an toàn và C2 exact-item automatic-completion research probe có thể kiểm thử local trước khi xin một live attempt riêng.

**Architecture:** Giữ pipeline Python controller → Node launcher → Python probe. Thêm schema/candidate v2, isolated two-fragment experiment và session-aware cleanup, đồng thời đọc nguyên trạng ledger C1 bằng compatibility branch.

**Tech Stack:** Python `>=3.12`, MSAL hiện có, httpx, pytest, Ruff `0.6.0`, Node.js ESM; không thêm dependency.

**Spec:** [ADR 0042](../adr/0042-onedrive-personal-protected-values-and-sync-write-transactions.md), [PR-07 contract](../implementation/VALORA_UIUX_V2_3_PR07_SYNC_CONFLICT_CONTRACT.md) là accepted authority; §§4–8 dưới đây là proposed research specification, không thay accepted D6.

**Task:** `VALORA-PR07-CONFORMANCE-001` — G1 local implementation. **Ngày:** 2026-09-18,
Asia/Saigon. **Trạng thái:** G2 LIVE COMPLETE — INCONCLUSIVE; G3–G4 CLOSED.
**Runtime PR-07:** BLOCKED.

**Global constraints:** “No secrets committed; no production credentials in repo.”; “No unrelated refactors or formatting churn.”; “No deleting or weakening guardrails.”; “No skipped tests to hide failures.” Các giới hạn scope/authority cụ thể ở §§1–3 áp dụng cho mọi task.

## 1. Kết quả cần đạt và ranh giới phê duyệt

Chuẩn bị một candidate có thể giải thích lỗi OAuth an toàn và kiểm chứng liệu upload session gắn với exact item có từ chối stale write khi tự hoàn tất ở fragment cuối hay không. Không chạy lại C1 nguyên trạng. Không diễn giải kết quả C2 thành việc ADR 0042/D6 đã được đáp ứng.

Yêu cầu G0 ban đầu của Product Owner: **“Viết implementation chi tiết trước khi tiến hành”**.
Authority đó chỉ cho phép viết và kiểm tra tài liệu; các approval G1/G2 tách biệt và kết quả thực thi
được ghi tại §13.

| Gate | Phạm vi | Điều kiện chuyển tiếp |
| --- | --- | --- |
| G0 — plan | Tài liệu này và navigation link | Product Owner duyệt phạm vi local correction + independent review |
| G1 — local candidate | Ba tools, hai test files và docs liên quan; fake provider, no-external-network tests | Local verification đạt, independent review không còn finding cần xử lý, ghi đúng source hashes |
| G2 — research live | Đúng một controller invocation C2 trên isolated fixture; một fresh branch và một stale branch nếu fresh đạt | Fresh action-time approval, chấp thuận ngoại lệ nghiên cứu C2 so với D6, chuẩn bị quyền tạm và xác minh cleanup baseline |
| G3 — architecture decision | Xem bằng chứng C2, quyết định có sửa D6 hay cần nghiên cứu thêm | Product Owner quyết định rõ; không mở runtime chỉ bằng một observation |
| G4 — PR-07 runtime | Sync/conflict, persistence, migrations, UI và recovery theo contract được chấp thuận | Gate provider/architecture đã đóng và phạm vi thực thi được xác nhận riêng |

Nếu G1 review có finding, báo findings và dừng ở gate; không tự mở thêm vòng correction/review ngoài số vòng được duyệt. G2 thất bại ở OAuth cũng kết thúc lần live đó: không đổi secret rồi thử lại, không chuyển C1, không tiếp tục bằng tool ngoài controller.

## 2. Baseline, nguồn và sự thật đã xác minh

- Branch: `feat/operational-frontend-m365`; HEAD khi lập plan: `46e0792b3ae697158f0fe38db8100fbd4afdc6fc`.
- `origin/main` sau `git fetch origin`: `27d1cc630f97cb9b56fbfbb4c5bc04d4be305cc6`.
- Trước tài liệu này, working tree chỉ có `scratch/` chưa tracked; không đọc, sửa, stage hoặc xóa thư mục đó.
- Bộ `68/68` và self-test PASS là bằng chứng C1 lịch sử tại candidate đã review, không phải kết quả kiểm thử C2 hoặc lần lập plan này.
- Live gần nhất dừng ở `OAUTH_TOKEN_REJECTED`, chưa chạy launcher/probe/Graph. Việc cleanup Entra đã được Product Owner xác nhận; không tái dùng authority của lần đó.
- Mã controller hiện gom lỗi MSAL vào `OAUTH_TOKEN_REJECTED`. Probe hiện gửi toàn bộ payload `320 KiB` trong staging; stale status khác `412` bị raise trước post-state read. C2 phải thay cả ba hành vi liên quan, không chỉ đổi `deferCommit`.
- MSAL cài local khi kiểm tra: `1.38.0`. `obtain_token_by_auth_code_flow` kiểm state trước xử lý callback; callback error có thể trả error dictionary mà không redeem code. Cần giữ đường kiểm tra này.

Nguồn có thẩm quyền:

- [CODEX.md](../../CODEX.md), [engineering guardrails](../../ENGINEERING_GUARDRAILS.md).
- [ADR 0042](../adr/0042-onedrive-personal-protected-values-and-sync-write-transactions.md), đặc biệt D6, D7, D9.
- [PR-07 sync/conflict contract](../implementation/VALORA_UIUX_V2_3_PR07_SYNC_CONFLICT_CONTRACT.md), phần provider commit, recovery, acceptance và stop condition.
- [Provider runbook](../implementation/VALORA_UIUX_V2_3_PR07_PROVIDER_CONFORMANCE_RUNBOOK.md), [acceptance matrix](../implementation/VALORA_UIUX_V2_3_PR00_PR13_FEATURE_ACCEPTANCE_MATRIX.md), [research handoff](../research/pr07-onedrive-conformance-handoff.md).

Research input: `PR-07_OneDrive_Provider_Conformance_Research_Report_2026-09-18.md`, file Product Owner cung cấp từ `E:/Nhap/`, SHA-256 `194aba8b7cb0fb459f2fc3a428380a07785916c806c3dec215e93b2bf180ba1d`. Không copy file ngoài repo hoặc sửa nội dung report trong task này. Các đề nghị trong report là input nghiên cứu, không phải lệnh thực thi hay amendment đã được chấp thuận.

Tài liệu Microsoft được đối chiếu ngày 2026-09-18:

- [Graph v1.0 createUploadSession](https://learn.microsoft.com/en-us/graph/api/driveitem-createuploadsession?view=graph-rest-1.0): có route cập nhật bằng item ID, `If-Match` khi tạo session, mặc định conflict `fail`, automatic completion khi không bật `deferCommit`. Chưa thấy bảo đảm rõ rằng precondition tạo session được kiểm lại ở final fragment; đó là giả thuyết cần thử, không phải fact đã chứng minh.
- [Update driveItem](https://learn.microsoft.com/en-us/graph/api/driveitem-update?view=graph-rest-1.0): metadata update dùng `PATCH`; không dùng trang này để suy ra bare-item `PUT` của C1 được hỗ trợ.
- [MSAL token acquisition](https://learn.microsoft.com/en-us/entra/msal/python/getting-started/acquiring-tokens): tham khảo flow; phân loại cụ thể phải được test với thư viện thực tế, không dựa vào callback HTML.

Các sửa đổi về cách kết luận so với research input: tiêu chí chốt trước run; thiếu documentation không đồng nghĩa chứng minh không hỗ trợ; ambiguous là INCONCLUSIVE, không phải provider impossibility; một kết quả safe chỉ là bằng chứng của trường hợp đã chạy.

## 3. Scope lock và impact map

Không thêm dependency, generic provider framework hoặc cơ chế chọn thử nhiều wire shapes. Dùng ba tools hiện có. C1 chỉ được giữ qua Git history và reader bằng chứng cũ; không duy trì hai live mechanisms hoạt động song song.

| File | Điểm sửa dự kiến sau G0 | Kiểm chứng bắt buộc |
| --- | --- | --- |
| [live controller](../../backend/tools/pr07_onedrive_personal_live_controller.py) | `_acquire_live_access_token`, callback copy, candidate CLI/argv, `AttemptRecorder`, report validators, prior-attempt scanner và journal lifecycle | OAuth state/redaction, candidate binding, old/new ledger compatibility, no-network integration |
| [probe](../../backend/tools/pr07_onedrive_personal_if_match_probe.py) | `_create_upload_session`, thay `_stage`/`_commit` bằng partial/final upload, `run`, report/failure model và cleanup | Exact wire shape, actual mutation model, post-state mọi terminal outcome, no retry |
| [Node launcher](../../backend/tools/pr07_onedrive_personal_if_match_launcher.mjs) | `parseArguments`, candidate propagation, `validateReport`, exit/status mapping | Absolute Python argv, bounded output, exact C2 schema, reject downgrade |
| [controller tests](../../backend/tests/test_pr07_onedrive_personal_live_controller.py) | OAuth cases, candidate-aware reports/journals, lifecycle adversarial cases | Gồm MSAL state check thật với transport stub; không fake state validation thành PASS |
| [probe/launcher tests](../../backend/tests/test_pr07_onedrive_personal_if_match_probe.py) | C2 stateful fake, chunking, unsafe/unknown paths, shared validator vectors | Fake phải mô phỏng write thực sự, không chỉ đổi HTTP status |
| Provider runbook + acceptance matrix + plan này | Sau thực thi mới cập nhật local evidence và cách chạy C2 | Không ghi provider PASS, READY hoặc runtime implemented khi chưa có bằng chứng |

Không đụng `backend/app/**`, DB/Alembic, frontend, worker, PR-05 credential flow, production credentials, accepted ADR/contract hoặc PR-08. Không commit/push/PR/merge/deploy trong phạm vi này nếu chưa có yêu cầu riêng. Không sửa lịch sử research để biến quan sát cũ thành kết luận mới.

## 4. Thiết kế OAuth diagnostics

### 4.1 Flow và mã lỗi

1. Giữ nguyên consumer authority, confidential client, delegated `Files.ReadWrite`, redirect URI, `form_post`, callback body bound và no-query callback.
2. Trước MSAL, chỉ nhận diện shape trong memory: đúng một non-empty `code` hoặc `error`. Cả hai, thiếu cả hai hoặc sai kiểu là malformed và bị từ chối trước redemption, không ghi nội dung callback. Structural rejection không được báo thành authorization rejection đã qua state validation.
3. Với shape hợp lệ, luôn gọi MSAL để kiểm state/PKCE/flow. Không return sớm chỉ vì callback có `error`.
4. Chỉ sau MSAL trả về hợp lệ mới phân biệt authorization-response rejection với code-redemption rejection. Nhãn `TOKEN_REDEMPTION` mô tả nhánh thực thi, không chứng minh một HTTP token request đã thực sự đi ra.
5. `finally` bao toàn bộ xử lý callback, kể cả malformed input: `callback_response.clear()` và `_CallbackHandler.callback_response = None`. Không đưa callback, flow hoặc exception text vào recorder.
6. Giữ nguyên validation issuer, tenant, audience, subject và granted scopes cho success. Không thay result bằng token do callback cung cấp.

| Tình huống | Local failure code | Diagnostic phase |
| --- | --- | --- |
| Validated callback error | `OAUTH_AUTHORIZATION_REJECTED` | `AUTHORIZATION_RESPONSE` |
| Callback code, MSAL trả error dictionary | `OAUTH_TOKEN_REDEMPTION_REJECTED` | `TOKEN_REDEMPTION` |
| Callback thiếu/có cả code và error | `OAUTH_RESPONSE_MALFORMED` | `CALLBACK_VALIDATION` |
| MSAL validation exception | `OAUTH_FLOW_VALIDATION_FAILED` | `FLOW_VALIDATION`; không khẳng định mọi ValueError đều là bad state |
| MSAL trả sai result shape | `OAUTH_RESULT_MALFORMED` | `RESULT_VALIDATION` |
| Browser, timeout, account hoặc scope bị từ chối | Giữ các code hiện hành tương ứng | Giữ đúng stage; không gộp thành token rejection |
| Exception không phân loại được | `OAUTH_FLOW_FAILED` | `UNKNOWN`; không serialize exception |

HTML callback dùng “Authorization response received.”; thông báo chỉ xác nhận receipt, không khẳng định OAuth thành công. Không render bất kỳ trường nhận từ provider vào HTML.

### 4.2 Schema diagnostics khóa trước implementation

`failure_details` của lỗi OAuth schema v2 chỉ chứa một object `oauth` với đúng các key dưới đây. Trường không có dữ liệu dùng `null`/list rỗng; không thêm raw fallback.

| Key | Kiểu/giới hạn |
| --- | --- |
| `phase` | Enum ở bảng trên |
| `oauth_error` | `access_denied`, `invalid_request`, `invalid_client`, `invalid_grant`, `unauthorized_client`, `unsupported_grant_type`, `invalid_scope`, `interaction_required`, `login_required`, `consent_required`, `server_error`, `temporarily_unavailable`, `unknown`, hoặc `null` |
| `aadsts_codes` | Tối đa 8 số nguyên thực sự trong `0..2147483647`, loại boolean, unique và sort; chỉ lấy structured `error_codes` |
| `correlation_id` | UUID canonical hợp lệ hoặc `null`; không coi regex gần giống UUID là hợp lệ |

Không parse `error_description` trong v1 này: chấp nhận thiếu AADSTS khi MSAL không cung cấp structured data. Như vậy không cần thêm text parser có nguy cơ giữ raw message. Với error callback, nếu cần correlation/error_codes mà MSAL không forward, chỉ dùng bản normalize trong memory sau khi state validation thành công. Mọi giá trị malformed/unknown bị bỏ hoặc map `unknown`, không echo nguyên văn.

Writer và v2 reader cùng kiểm exact keys, types, count/range và tổng diagnostic object tối đa 1 KiB serialized UTF-8. Khi encoder nhận internal diagnostic không hợp lệ, thay bằng failure code cố định, không serialize dữ liệu lỗi; khi reader thấy artifact sai schema, fail closed. Canary scan là kiểm tra bổ sung, không thay allowlist. Không lưu code, state, PKCE verifier, token, secret, claims, provider body hay raw stderr.

Quy mô rủi ro: phạm vi dự kiến một operator trên máy local; callback bên ngoài và token result đều là dữ liệu không tin cậy. Không cần giả định kẻ tấn công có động cơ đặc biệt: log nhầm đã có thể làm lộ credential. Chọn validation tại boundary sẵn có và test canary, không thêm một hệ thống telemetry. Các giới hạn 8 code/1 KiB là quyết định thiết kế bảo thủ, không phải thống kê provider; nếu diagnostics hợp lệ thực tế vượt giới hạn thì review version mới, không tự nới tại runtime.

## 5. C2 wire protocol và thuật toán

### 5.1 Identity và wire shape cố định

Candidate duy nhất: `C2_AUTO_V1`. Controller live bắt buộc `--candidate C2_AUTO_V1`; thiếu/sai/C1 bị từ chối trước OAuth. Self-test C2 dùng cùng candidate explicit. Không nhận candidate khác từ report để thay giá trị đã yêu cầu.

Fixture là một `.bin` mới với tên deterministic theo attempt UUID, thuộc Personal account của Product Owner. Chỉ fixture setup/recovery trước khi có ID được dùng tên. Khi có bound identity, mọi thao tác trên destination dùng đúng drive/item ID. Không nhận arbitrary existing user item từ CLI.

```http
POST /v1.0/drives/{driveId}/items/{itemId}/createUploadSession
If-Match: {frozenETag}
Content-Type: application/json

{}
```

Body `{}` được chốt: không `deferCommit:true`, không `item`, `name`, `fileSize`, `replace` hoặc `rename`. Dùng conflict `fail` mặc định, không tự thử thêm annotation khi lỗi. Nếu shape này không được provider chấp nhận thì ghi observation và dừng.

Payload tổng `655360` bytes, hai fragments tuần tự:

```text
Fragment 1: Content-Length 327680; Content-Range bytes 0-327679/655360
Fragment 2: Content-Length 327680; Content-Range bytes 327680-655359/655360
```

Hai request PUT gửi tới upload URL trong memory, không `Authorization`, không thêm `If-Match` ở final fragment và không explicit `sourceUrl` completion. C2 kiểm retention của session precondition; thêm final header sẽ thành giả thuyết khác. Không tự follow mutation redirects, resend fragment hoặc tạo session thay thế.

Fresh và stale dùng cùng endpoint/body/chunk sizes/settings. Các payload original, fresh, stale, concurrent có cùng size, nội dung deterministic nhưng khác nhau; so sánh checksum chỉ trong memory. `/content` chỉ còn ở fixture setup và writer mô phỏng cạnh tranh, không trở thành cơ chế sync fallback.

### 5.2 Fresh control

1. Xác minh Personal drive, tạo fixture; đọc metadata + bytes xác nhận item ID, eTag `E0` và original payload.
2. Ghi journal trước request tạo fresh session với `If-Match: E0`; giữ upload URL trong memory.
3. PUT fragment 1 đúng một lần; capture response/status/range hoặc transport failure, không raise bỏ qua post-read. Kỳ vọng `202` và expected remaining range đúng `327680-`; không tự sửa range theo response bất thường.
4. Sau mọi fragment 1 đã dispatch, kể cả `200/201`, malformed range hoặc timeout, đọc lại exact destination để kiểm ID, eTag `E0`, original bytes. Nonfinal mutation đã xác minh là safety violation; read không xác minh được là INCONCLUSIVE. Chỉ đi final nếu `202`, range hợp lệ và destination chưa đổi đều được chứng minh.
5. Persist `FRESH_FINAL_FRAGMENT_REQUEST_STARTED` trước I/O; PUT fragment 2 đúng một lần.
6. Dù response là success/error hoặc transport exception sau dispatch, thực hiện bounded post-state read trước cleanup. Một observation dùng metadata-before → content → metadata-after; hai metadata phải cùng identity/eTag để tránh ghép hai phiên bản. Không tự polling/retry nếu đọc không nhất quán.
7. Chỉ sang stale branch khi có `200/201`, response identity hợp lệ, exact reread đúng fresh bytes và eTag mới khác `E0`. Nếu thiếu điều kiện, kết thúc attempt với observation phù hợp.

### 5.3 Stale race

1. Freeze eTag fresh `E1`; tạo stale session với `If-Match: E1` và cùng wire shape.
2. Upload fragment 1 đúng một lần; sau mọi dispatched outcome đều coherent reread như fresh branch. Chỉ tiếp tục nếu `202`, remaining range hợp lệ và destination vẫn đúng fresh bytes/`E1`; unexpected status không được bỏ mất bằng chứng nonfinal mutation.
3. Đây là precommit reread cuối của writer đang giữ session. Sau đó fixture writer dùng conditional `/content` với `If-Match: E1` ghi concurrent payload.
4. Harness đọc xác minh cùng item, eTag `E2 != E1` và concurrent bytes. Đây là assertion thiết lập race, không cập nhật frozen precondition của stale session.
5. Persist `STALE_FINAL_FRAGMENT_REQUEST_STARTED`; gửi fragment 2 đúng một lần từ session vẫn gắn `E1`. Cố ý không dùng client-side stale guard để chặn request: thí nghiệm phải kiểm khả năng bảo vệ của provider.
6. Capture response metadata allowlisted hoặc transport outcome, rồi luôn thử coherent post-state read trước cleanup. So sánh destination với concurrent và stale payload trong memory.
7. Classify theo §6, đóng/cancel session theo §7, recycle fixture, finalize bằng chứng. Không tiếp tục bằng request khác nếu kết quả không như mong đợi.

Ngoại lệ bước 5 chỉ dành cho isolated negative test. Runtime tương lai vẫn phải reread trước commit và đồng thời có provider-side protection cho race xảy ra sau reread.

## 6. Acceptance matrix chốt trước live

Các kết luận stale dưới đây yêu cầu fresh control đạt và race đã được thiết lập/đọc xác minh. Không đủ precondition thì `INCONCLUSIVE`, không gán false cho phép kiểm chưa chạy.

| Quan sát | `outcome` | Kết luận/next action |
| --- | --- | --- |
| Stale `412`, exact identity và concurrent bytes/eTag được bảo toàn | `OBSERVED_SAFE_STALE_REJECTION` | Bằng chứng tích cực của một case; đưa sang G3, chưa mở runtime |
| Destination bị thay bằng stale candidate sau concurrent write đã xác minh, kể cả response timeout hoặc báo `412` | `UNSAFE_STALE_OVERWRITE` | Bác bỏ C2_AUTO_V1 trong điều kiện đã thử; không suy rộng toàn bộ OneDrive |
| Identity thực sự thay đổi hoặc destination mutate ở nonfinal fragment | `SAFETY_VIOLATION` | Dừng candidate; mô tả invariant đã vi phạm, không xóa observation khi cleanup lỗi |
| `409`/status khác `412`, concurrent bytes còn nguyên | `INCONCLUSIVE` | Ghi alternate rejection; không đổi tiêu chí HTTP sau run |
| Final `202`, `5xx`, timeout và chưa thấy overwrite đã xác minh | `INCONCLUSIVE` | Không resend/fallback; kiểm post-state và cleanup |
| OAuth/fresh/session failure, concurrent setup thất bại, post-state unavailable/inconsistent hoặc third-state bytes | `INCONCLUSIVE` | Ghi boundary đã tới và dữ kiện còn thiếu |
| Response trả ID khác nhưng bound-item reread chưa chứng minh identity đổi | `INCONCLUSIVE` | Sai response identity; không target ID lạ để cleanup hoặc gọi đó là proven replacement |

`status=PASS` và exit `0` chỉ khi `OBSERVED_SAFE_STALE_REJECTION`, mọi required check đã xác minh và cleanup/evidence hoàn tất. Đây là **C2 research observation PASS**, không phải accepted D6 conformance PASS. Tất cả kết quả khác dùng `status=FAIL`, exit `1`; argument parsing giữ nonzero fail-closed. `runtime_gate` luôn là `BLOCKED`.

Cleanup failure không đổi `outcome` đã quan sát thành `INCONCLUSIVE`; nó đổi overall status thành FAIL và giữ riêng cleanup result. Khi verification chưa đủ thì nullable check giữ `null`, không mặc định `true` hoặc `false`.

## 7. Session, cleanup và durable journal

### 7.1 State machine cần chứng minh

```text
NO_SESSION → CREATE_STARTED/UNKNOWN → OPEN
OPEN → PARTIAL_STAGED → FINAL_STARTED/MAY_HAVE_COMMITTED
FINAL_STARTED → COMPLETED_PROVEN hoặc STILL_OPEN_OR_UNKNOWN
OPEN/STILL_OPEN_OR_UNKNOWN → CANCEL_STARTED → CANCELLED_OR_ABSENT
Sau khi xử lý session → ITEM_DELETE_STARTED → ITEM_DELETED → TERMINALS
```

Phân biệt session đã đóng với bytes đúng: response final completion hợp lệ có thể chứng minh session đóng dù destination bytes không đạt. Không dùng một marker “read started” để chứng minh completion hoặc verification.

| Tình huống | Cleanup và ledger |
| --- | --- |
| Final completion được chứng minh bằng response hợp lệ và post-state coherent | Emit completed/proven marker rồi đóng session state; fresh đạt mới được tạo stale session |
| Final thất bại hoặc response mất, vẫn có upload URL | Giữ URL trong memory; sau post-read, cancel một lần, rồi recycle exact fixture |
| Cancel trả `204` hoặc `404` | Chứng minh capability hiện đã hủy/không tồn tại, không chứng minh final chưa từng ghi |
| Cancel lỗi | Vẫn thử exact-item deletion; overall FAIL, unresolved nếu session chưa được giải quyết |
| Create-session đã gửi nhưng mất response/không có upload URL | Session UNKNOWN; item deletion riêng không đủ chứng minh session đóng; block future live |
| Item create mất response trước khi có ID | Chỉ bounded cleanup theo tên fixture deterministic; không scan/delete item khác |
| Exact-item deletion trả `404` hoặc lỗi | Giữ fail-closed hiện hành; không giả định đã recycle thành công |
| Journal write lỗi trong cleanup | Cleanup vẫn best effort; không tạo completion marker giả; ledger unresolved nếu thiếu bằng chứng |
| Process chết, thiếu terminal, event đảo thứ tự hoặc có mutation sau deletion | UNKNOWN; next live bị chặn trước OAuth |

Không nới quy tắc session UNKNOWN chỉ để run sau đi tiếp. Cancel không phải rollback. Cleanup fixture chỉ tác động file thử nghiệm, không được copy thành recovery của tài liệu thật. Entra secret/permission cleanup vẫn là bước riêng do operator xác minh; JSON của controller không chứng minh cloud cleanup.

### 7.2 Events và ordering cho v2

Giữ event schema nhỏ và tách reader C1/v2. V2 có enum `session_role=FRESH|STALE` ở session events, không ghi session URL/ID. Các logical events cần có:

- Session create request started; session URL validated/available.
- Partial fragment request started; partial response validated; destination preservation verified.
- Final fragment request started **trước mutation**; final response observed hoặc transport outcome unknown.
- Post-state read started; post-state verification completed chỉ sau coherent observation.
- Session completion proven hoặc cancel started/completed, với cùng role.
- Fixture create/delete started/completed; probe terminal; controller terminal.

Chốt enum/key schema trong test vectors trước sửa producer. Các mutation-start markers phải có mặt trong `PROVIDER_MUTATION_STAGES`; read/verification stages không được dùng để suy ra mutation chưa xảy ra. Scanner phải biết session nào đang active, partial đã hoàn tất chưa, final chỉ gửi một lần và cancellation pending không được chen stage khác.

Đối chiếu `PROBE_FINISHED`, launcher report và `ATTEMPT_FINISHED`: same candidate, same schema, same observation/status/exit/cleanup. V2 marker không được xuất hiện trong legacy journal. Không có stage sau terminal. Để **resolve** ledger, delete markers phải đứng sau mutation cuối và sau session close/cancel được chứng minh. Best-effort deletion sau cancel failure/session UNKNOWN vẫn phải chạy và ghi nhận đúng dù không thỏa điều kiện resolve; đó là journal của một attempt unresolved, không phải lý do cấm cleanup hoặc giả close marker.

## 8. Evidence schema và compatibility

### 8.1 Schema v2

Tăng snapshot `schema_version` từ `1` lên `2`; `ATTEMPT_STARTED` có `schema_version=2` và `candidate=C2_AUTO_V1`. Candidate phải được truyền controller → Node → probe và kiểm bằng requested candidate, không chỉ kiểm thuộc allowlist. Cùng thông tin xuất hiện trong terminal report và controller summary để operator không đọc nhầm PASS.

Report C2 live dùng exact keys, không reuse `fresh_conditional_commit`/`HTTP_412_PASS` của C1:

| Nhóm | Fields/types |
| --- | --- |
| Identity của thí nghiệm | `schema_version: 2`, `candidate: C2_AUTO_V1`, `runtime_gate: BLOCKED`, `checked_at` UTC hợp lệ |
| Kết quả | `status: PASS|FAIL`, `outcome` theo §6, `reason_code` enum cố định theo các case §6/§7 |
| Phase | `phase: FIXTURE|FRESH|STALE|COMPLETE`; giữ phase kết quả chính khi cleanup lỗi |
| HTTP | `fresh_final_http_status`, `stale_final_http_status`: integer `100..599` hoặc `null`, cấm boolean |
| Provider code | `provider_error_code`: enum known code hoặc `unknown`/`null`; không đưa raw provider message vào report |
| Checks | Object exact keys: `fresh_partial_preserved`, `fresh_commit_verified`, `stale_partial_preserved`, `concurrent_write_verified`, `item_identity_preserved`, `concurrent_bytes_preserved`, `concurrent_etag_preserved`, `stale_candidate_observed`; mỗi giá trị `true|false|null` |
| Cleanup | `cleanup: NOT_ATTEMPTED|DELETED_TO_RECYCLE_BIN|ABSENT_OR_DELETED_TO_RECYCLE_BIN|FAILED`; `cleanup_issue: NONE|SESSION_UNKNOWN|CANCEL_FAILED|ITEM_DELETE_FAILED|EVIDENCE_INCOMPLETE|MULTIPLE` |

`reason_code` initial set: `SAFE_412`, `STALE_BYTES_OVERWROTE_CONCURRENT`, `NONFINAL_MUTATION`, `IDENTITY_CHANGED`, `RESPONSE_IDENTITY_MISMATCH`, `ALTERNATE_REJECTION`, `FINAL_NOT_COMPLETED`, `TRANSPORT_UNKNOWN`, `POST_STATE_UNAVAILABLE`, `POST_STATE_INCONSISTENT`, `THIRD_STATE`, `FRESH_CONTROL_FAILED`, `RACE_SETUP_FAILED`, `SESSION_CREATION_FAILED`, `FIXTURE_FAILED`, `UNEXPECTED_SANITIZED_FAILURE`. `provider_error_code` initial known set: `accessDenied`, `invalidRequest`, `invalidRange`, `nameAlreadyExists`, `resourceModified`, `itemNotFound`, `quotaLimitReached`, `tooManyRequests`, `generalException`; các giá trị khác map `unknown`. Enum ghi nhận, không tự quyết định PASS.

Cross-field predicate bắt buộc: safe observation cần fresh final `200/201`, stale final `412`, bảy checks đầu `true` và `stale_candidate_observed=false`. Unsafe overwrite cần fresh/race đã verified, coherent same-item read có `stale_candidate_observed=true` và `concurrent_bytes_preserved=false`, không phụ thuộc stale HTTP status. `status=PASS` còn cần `phase=COMPLETE`, `reason_code=SAFE_412`, cleanup `DELETED_TO_RECYCLE_BIN`, issue `NONE`. Safe observation kèm cleanup lỗi vẫn giữ outcome/checks nhưng overall FAIL. Không cho enum outcome tự thay cho các predicates này.

Self-test dùng schema riêng exact-key có `schema_version`, `candidate`, `mode=SELF_TEST`, `network=NOT_ATTEMPTED` và các launcher checks hiện hành; không có provider outcome giả. Lỗi controller/launcher trước probe vẫn là report boundary riêng, không bịa report C2 khi probe chưa chạy. OAuth details thuộc controller, không lan sang Node/probe.

Các điểm phải cập nhật cùng nhau: probe `_valid_diagnostic_report`/result writer; launcher `validateReport`; controller `_validate_probe_report`, `validate_launcher_report`, `_terminal_reports_are_consistent`, `AttemptRecorder.finish`, prior-ledger reader. `ProbeFailure.with_cleanup` không được làm mất observation/checks khi thêm cleanup failure.

Không lưu drive/item IDs, eTags, filenames của tài liệu người dùng, upload/download URLs, content hoặc content hashes trong artifacts. Code/Git component hashes được giữ như hiện tại; content comparisons chỉ xuất thành bounded checks.

### 8.2 Legacy compatibility và chống downgrade

1. Journal lịch sử thiếu schema/candidate chỉ đi qua C1 legacy reader, giữ nguyên điều kiện `412`, exact terminal schema và cleanup rules; không rewrite file cũ.
2. Current v2 invocation không chấp nhận output thiếu schema/candidate dù legacy decoder nhận dạng được shape đó.
3. Version/candidate lạ, header v2 nhưng report C1, mixed stages hoặc mismatch request/report đều fail closed.
4. Legacy attempt unresolved vẫn chặn C2. Candidate mới không reset quyền ghi hoặc xóa yêu cầu cleanup.
5. Nếu legacy artifact thật không khớp fixtures, dừng để reconcile có bằng chứng; không xóa ledger, đổi evidence directory hoặc nới parser.

Không thêm generic schema registry. Một legacy branch được cô lập và một v2 branch rõ ràng là đủ. Dùng cùng tập fixtures/vector do tests tạo để so sánh các validators Python/Node, tránh thêm dependency chỉ để share schema.

## 9. Test matrix và lệnh verification

Tất cả test dưới đây dùng fake/stub hoặc loopback local; không OAuth/Graph/Entra thật. Không lấy test count lịch sử làm target cố định. Báo số pass/fail/skip thực tế; skip không phải PASS.

| ID | Test bắt buộc | Assertion quyết định |
| --- | --- | --- |
| O1 | Callback `access_denied`, state hợp lệ | Authorization phase; không token redemption; callback cleared |
| O2 | Code flow `invalid_client`/`invalid_grant`/`invalid_scope` | Redemption phase, normalized details, không raw description |
| O3 | State sai/thiếu; code+error; thiếu cả hai | Fail closed; không token redemption; không copy exception state vào report |
| O4 | Unknown error, malformed/non-dict result, bool AADSTS, oversize list, bad UUID | Schema bounds đúng, không crash/leak |
| O5 | MSAL exception và account/scope failure | Callback cleared ở mọi exit; validations hiện hành không yếu đi |
| O6 | Canary trong nested callback/result/description/claims/exception | Không xuất trong stdout, stderr, HTML, snapshot, journal |
| P1 | Fresh success + stale `412` đúng | Hai fragments mỗi branch; đúng ranges/ID/eTag; đủ checks; observation PASS |
| P2 | Stale `200/201` thực sự overwrite | `UNSAFE_STALE_OVERWRITE`; post-state vẫn chạy; chỉ một final PUT |
| P3 | `412` nhưng fake đã mutate; case khác giữ bytes nhưng đổi eTag | Không false PASS; unsafe nếu stale bytes đã overwrite, INCONCLUSIVE nếu chỉ eTag khác và bytes vẫn giữ |
| P4 | `409`, final `202`, `5xx` với bytes giữ nguyên | INCONCLUSIVE, có post-read, không fallback/retry |
| P5 | Response lost trước và sau actual commit | Tách được observed overwrite với unknown; no retransmission |
| P6 | Nonfinal mutation kèm partial `201`, range lỗi hoặc response lost; fresh wrong bytes/ID/eTag | Partial error vẫn post-read và ghi safety violation khi đã chứng minh mutation; không stale branch nếu fresh không đạt |
| P7 | Partial wrong range/overlap/order; concurrent setup không đổi bytes/eTag | Không tính là phép thử stale hợp lệ |
| P8 | Metadata thay giữa content read; read timeout; third-state bytes | Không kết luận dựa snapshot ghép; null checks khi chưa biết |
| C1 | Known session cancel `204/404/error`; delete `204/404/error` | Giữ phân biệt session absence, commit state và recycle evidence |
| C2 | Create session response lost; missing upload URL | Không resolve chỉ vì item đã delete |
| C3 | Journal hỏng ngay trước final mutation | Không gửi final PUT; cleanup vẫn best effort |
| C4 | Journal lỗi trong cleanup; cancel exception | Vẫn thử delete; giữ primary observation và cleanup issue |
| J1 | Legacy resolved/unresolved fixtures hiện hành | Kết quả cũ giữ nguyên; unresolved vẫn chặn trước OAuth |
| J2 | Unknown/mixed schema, candidate mismatch, missing terminal, boolean exit code | Mọi consumer từ chối nhất quán |
| J3 | Final trước partial, stage sau terminal/delete, fake read-start closure, cancellation pending | Scanner không resolve lifecycle giả |
| J4 | Session complete proven nhưng outcome unsafe; OAuth-only failure không mutation | Cleanup resolution không đồng nghĩa provider PASS |
| L1 | Actual controller → Node → Python self-test từ path có spaces | Candidate xuyên suốt, `shell=False`, absolute interpreter một argv, no external network |
| L2 | Thiếu candidate/flags, C1 live, wrong app, noncanonical evidence directory | Reject trước browser/OAuth/client; no credential output |
| L3 | Cùng valid/invalid report vectors qua mọi validator | Không có producer PASS bị consumer reject hoặc unknown field được lọt |

Fake provider phải có state riêng cho content/eTag và upload range accumulation, chỉ auto-commit ở final fragment. Response status và việc mutate phải điều khiển độc lập, kể cả ném exception **sau** khi mutate. Fake hiện chỉ đổi `stale_status` không đủ làm bằng chứng cho P2/P3/P5.

O3 phải dùng logic state-validation thật của MSAL với HTTP transport stub, hoặc test double chứng minh không redeem khi state sai; không chỉ mock `acquire_token_by_auth_code_flow` trả dictionary. Tests không log raw canaries khi failure.

Các lệnh dự kiến sau implementation, chạy từ repo root bằng Python environment hiện hành có dependencies. Pytest chạy trong `backend/` vì tests và conftest import `tools`/`app` từ đó; khớp working directory của backend CI. Chưa chạy các lệnh này cho C2; flag C2 bên dưới chưa tồn tại ở baseline. Chạy từng lệnh, kiểm exit code ngay và dừng gate khi lỗi; không dùng exit code lệnh cuối để che lỗi trước:

```powershell
Push-Location backend
try {
    python -m pytest tests/test_pr07_onedrive_personal_if_match_probe.py tests/test_pr07_onedrive_personal_live_controller.py -q
    if ($LASTEXITCODE -ne 0) { throw 'Focused pytest failed.' }
} finally {
    Pop-Location
}
python -m ruff check backend/tools/pr07_onedrive_personal_if_match_probe.py backend/tools/pr07_onedrive_personal_live_controller.py backend/tests/test_pr07_onedrive_personal_if_match_probe.py backend/tests/test_pr07_onedrive_personal_live_controller.py
python -m py_compile backend/tools/pr07_onedrive_personal_if_match_probe.py backend/tools/pr07_onedrive_personal_live_controller.py
node --check backend/tools/pr07_onedrive_personal_if_match_launcher.mjs
python backend/tools/pr07_onedrive_personal_live_controller.py --self-test --candidate C2_AUTO_V1
git diff --check
```

Không chạy full integration cần DB/cloud để tạo cảm giác gate đã đạt. Nếu environment thiếu dependencies, báo blocker; không tự nâng MSAL hoặc thay Python executable để làm test xanh. Self-test thực tế phải kiểm artifacts có `network=NOT_ATTEMPTED`, candidate v2, không có canary và không lẫn provider observation.

## 10. Work packages, thứ tự và review gates

| WP | Deliverable sau khi được duyệt | Verify / exit condition |
| --- | --- | --- |
| WP0 | Ghi baseline SHA/status, kiểm unresolved ledger read-only, freeze schemas/test vectors | Không đụng scratch/credentials; không sửa ledger; scope đúng §3 |
| WP1 | OAuth classifier + bounded sanitizer + callback wording/clearing | O1–O6; không đổi PR-05 hoặc OAuth authority/scope |
| WP2 | C2 candidate propagation và schema v2 readers/writers | J1–J2, L2–L3; legacy evidence vẫn đọc, downgrade bị chặn |
| WP3 | Partial/final algorithm + coherent post-state + stateful fake | P1–P8; exact wire shape; final mutation không resend |
| WP4 | Session lifecycle, cleanup, journal reconciliation | C1–C4, J3–J4; unknown không thành resolved |
| WP5 | Full focused verification + exact subprocess self-test | Các lệnh §9 đạt, raw counts/hashes ghi nhận; không external network |
| WP6 | Independent review trên đúng final diff và hashes | Review OAuth secrecy/state, provider race, negative outcomes, schema parity, legacy ledger, cleanup và scope |
| WP7 | Cập nhật runbook/matrix/plan với kết quả thật; bàn giao G1 | Runtime vẫn BLOCKED; live vẫn NOT AUTHORIZED; nếu review fail, ghi findings và xin vòng mới |

Ưu tiên một implementation owner cho ba tools vì schema/lifecycle coupling; reviewer độc lập không sửa executable files trong cùng vòng. Không chia controller/probe/launcher cho ba người sửa schema song song. Không tạo commit/PR chỉ để đánh dấu WP nếu chưa có yêu cầu Git riêng.

G1 được coi hoàn tất khi có: diff gọn đúng paths, tests mới và regression đạt, self-test thật, secret-exclusion checks, independent review sạch, nguồn evidence gắn đúng hashes và tài liệu không tuyên bố đã chạy live. G1 không thể chứng minh behavior thật của Microsoft.

### 10.1 Task A — OAuth diagnostics, red/green cycle

**Files:** sửa `backend/tools/pr07_onedrive_personal_live_controller.py`; test tại `backend/tests/test_pr07_onedrive_personal_live_controller.py`. Không thêm module/service.

**Interface mới:** `_normalize_oauth_diagnostics(*, phase: str, payload: object) -> dict[str, Any]`, trả outer object `{"oauth": ...}` theo §4.2; chỉ nhận dữ liệu để normalize, không tự xác thực state. Caller chỉ persist sau validation hoặc dùng payload rỗng cho lỗi flow validation. Thêm `UUID` vào import `uuid` hiện có.

- [ ] Viết regression test dưới đây và các O1–O6; test helper đầu tiên phải fail vì helper chưa tồn tại.

```python
def test_oauth_diagnostic_normalizer_discards_untrusted_fields() -> None:
    details = live_controller._normalize_oauth_diagnostics(
        phase="TOKEN_REDEMPTION",
        payload={
            "error": "invalid_client",
            "error_codes": [7000215, True, "7000215", -1, 7000215],
            "correlation_id": "not-a-uuid",
            "error_description": "do-not-persist-this-description",
        },
    )
    assert details == {"oauth": {
        "phase": "TOKEN_REDEMPTION",
        "oauth_error": "invalid_client",
        "aadsts_codes": [7000215],
        "correlation_id": None,
    }}
```

- [ ] Từ `backend/`, chạy `python -m pytest tests/test_pr07_onedrive_personal_live_controller.py::test_oauth_diagnostic_normalizer_discards_untrusted_fields -q`; xác nhận FAIL do helper thiếu, không phải import/environment.
- [ ] Implement pure normalizer theo cấu trúc dưới đây; không nối raw error vào exception. `OAUTH_ERROR_ALLOWLIST` là đúng set §4.2 trừ `null`; `OAUTH_PHASES` là đúng tập phase §4.1. Đây là hằng số mới trong controller, không provider-controlled.

```python
def _normalize_oauth_diagnostics(*, phase: str, payload: object) -> dict[str, Any]:
    source = payload if isinstance(payload, dict) else {}
    error = source.get("error")
    if error is not None and (
        not isinstance(error, str) or error not in OAUTH_ERROR_ALLOWLIST
    ):
        error = "unknown"
    raw_codes = source.get("error_codes")
    codes = sorted({
        code for code in raw_codes
        if type(code) is int and 0 <= code <= 2147483647
    }) if isinstance(raw_codes, list) and len(raw_codes) <= 8 else []
    correlation = source.get("correlation_id")
    if isinstance(correlation, str) and re.fullmatch(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        correlation,
    ):
        correlation = str(UUID(correlation))
    else:
        correlation = None
    return {"oauth": {
        "phase": phase if phase in OAUTH_PHASES else "UNKNOWN",
        "oauth_error": error,
        "aadsts_codes": codes,
        "correlation_id": correlation,
    }}
```

- [ ] Integrate đúng flow §4.1: callback shape trong `try/finally`, MSAL state validation trước trusted phase, immediate clear, fixed failure codes và HTML receipt copy. Không đưa raw callback vào `ControllerFailure.details`.
- [ ] Chạy lại O1–O6 và controller regression suite. Expected: test normalizer PASS; MSAL invalid-state test chứng minh redemption count bằng 0; exception/rejection vẫn clear callback. Trước schema v2 hoàn chỉnh chỉ kiểm bằng test memory fixtures, không live/persist một format trung gian để làm evidence.

### 10.2 Task B — candidate binding và evidence v2

**Files:** ba tools §3 và hai test files. **Interface changes:** `build_launcher_command` thêm keyword-only `candidate: str`; launcher `validateReport(report, selfTest, token, expectedCandidate)` nhận expected candidate bắt buộc; controller validators thêm `expected_candidate: str` cho current invocation. Legacy scanner dispatch reader theo header, không dùng default parameter để tự downgrade.

- [ ] Thêm tests thiếu/sai candidate, explicit C1 live, current output thiếu schema, mixed C1/v2 và normalized OAuth details sai shape. Expected RED ở baseline: parser chưa có candidate hoặc validator chưa biết v2.
- [ ] Wire CLI qua ba tầng, không shell string. Các cặp argv mới là `['--candidate', 'C2_AUTO_V1']`; test absolute Python vẫn là một argv element.
- [ ] Implement schema/header dispatch, exact-key/type và cross-field predicates §8; chuẩn bị positive vector hoàn chỉnh sau để đưa qua cả ba validators.

```python
safe_c2_report = {
    "schema_version": 2,
    "candidate": "C2_AUTO_V1",
    "runtime_gate": "BLOCKED",
    "checked_at": "2026-09-18T00:00:00+00:00",
    "status": "PASS",
    "outcome": "OBSERVED_SAFE_STALE_REJECTION",
    "reason_code": "SAFE_412",
    "phase": "COMPLETE",
    "fresh_final_http_status": 200,
    "stale_final_http_status": 412,
    "provider_error_code": None,
    "checks": {
        "fresh_partial_preserved": True,
        "fresh_commit_verified": True,
        "stale_partial_preserved": True,
        "concurrent_write_verified": True,
        "item_identity_preserved": True,
        "concurrent_bytes_preserved": True,
        "concurrent_etag_preserved": True,
        "stale_candidate_observed": False,
    },
    "cleanup": "DELETED_TO_RECYCLE_BIN",
    "cleanup_issue": "NONE",
}
```

- [ ] Tạo negative vectors bằng deep copy: đổi `stale_final_http_status=409`, đổi một required check thành `None`, thêm unknown key, đổi candidate, bỏ schema hoặc đưa boolean vào status. Giữ `status=PASS` để chắc mọi validator reject, không chỉ test producer tự chọn FAIL.
- [ ] Chạy controller/probe suites và Node validator tests; kỳ vọng mọi consumer thống nhất, J1 legacy fixtures giữ nguyên. Không gọi CLI live để test parse; tests phải stub browser/network và assert call count 0.

### 10.3 Task C — two-fragment algorithm và observations

**Files:** probe và probe tests. **Interfaces mới trong `OneDrivePersonalIfMatchProbe`:** `_upload_fragment(*, upload_url: str, content: bytes, start: int, total: int) -> httpx.Response`; `_read_coherent_item(*, drive_id: str, item_id: str) -> tuple[ItemState, bytes]`. Hai helpers không persist raw data. Caller giữ transport failure như observation UNKNOWN rồi post-read, không biến exception thành automatic retry.

- [ ] Nâng `GraphScenario` thành fake stateful theo §9; thêm P1–P8 trước thay live algorithm. Test trace phải phân biệt session create, partial PUT, final PUT, concurrent write và reads. Current C1 phải RED ở assertions exact two-fragment shape.
- [ ] Chốt payload `655360`, slice `content[:327680]` và `content[327680:]`. Xây headers từ fragment offset; kiểm trước I/O `len(content)==327680`, `total==655360`, `start in {0,327680}`; chỉ `run` điều khiển thứ tự, không gửi theo arbitrary provider range.

```python
headers = {
    "Content-Length": str(len(content)),
    "Content-Range": f"bytes {start}-{start + len(content) - 1}/{total}",
}
response = self._client.put(upload_url, headers=headers, content=content)
```

- [ ] `_read_coherent_item` gọi `_get_item`, `_download`, `_get_item` theo thứ tự; reject ID khác hoặc eTag trước/sau khác. Chỉ trả state+bytes khi coherent; không lưu checksum vào artifact.
- [ ] Thay `run` theo §§5.2–5.3: validate partial, preread, final-start durable marker, một PUT, post-read, classify; xóa C1 `_commit` khỏi active execution thay vì để đường fallback.
- [ ] Chạy P1–P8; assertion decisive của unsafe case là destination state đã đổi thật và `stale_candidate_observed=true`, không chỉ report HTTP 200. Mọi case final-dispatched phải assert post-read trước fixture delete và final PUT count bằng 1.

### 10.4 Task D — lifecycle, cleanup và handoff local

**Files:** probe/controller và hai test files, sau đó docs runbook/matrix. **Interfaces:** giữ `_has_unresolved_prior_live_attempt(evidence_directory: Path) -> bool`; bên trong dispatch legacy/v2. V2 resolver nhận ordered validated events và matching terminal reports, không chỉ list stage strings bỏ mất role/status.

- [ ] Thêm C1–C4/J3–J4 fixtures: mất create response, response-lost-after-commit, cancellation pending, read-start closure giả, terminal thiếu/khác report, mutation sau delete. Expected RED khi scanner còn suy completion từ read-start.
- [ ] Thay lifecycle bằng state transitions §7. Validate trước mutation, best-effort cleanup không phụ thuộc recorder khỏe; giữ primary outcome khi cleanup thêm lỗi. Không giả `SESSION_COMPLETED_PROVEN` để khỏi cancel.
- [ ] Chạy focused suite; đối với unsafe case cleanup đạt, scanner có thể resolve cleanup nhưng report vẫn FAIL. Đối với unknown session không có URL, exact-item deletion đạt vẫn phải block next live.
- [ ] Chạy đầy đủ lệnh §9 từng lệnh một, lưu counts/hashes và inspect sanitized self-test artifact. Self-test khác live approval.
- [ ] Reviewer độc lập đọc đúng diff và hashes; đối chiếu các predicates/schema/ordering chứ không chỉ chạy tests. Nếu có finding, báo gate chưa đạt; vòng sửa tiếp theo cần quyền theo §1.
- [ ] Cập nhật docs bằng bằng chứng đã chạy, kiểm links/whitespace, bàn giao G1; không tự commit/push hoặc đi G2. Nếu Product Owner yêu cầu commit sau đó, stage explicit paths thuộc task, tuyệt đối không stage `scratch/` hay local evidence.

## 11. Điều kiện và kịch bản G2 — đã thực thi đúng một lần

Checklist đã được đáp ứng trước lần live C2 duy nhất:

- [x] Product Owner duyệt C2 research exception: bỏ deferred explicit final commit để thử session-level concurrency; D6 production vẫn không đổi.
- [x] Product Owner cấp fresh action-time approval cho đúng một invocation trên candidate/hash đã review, gồm fixture creation, concurrent test write và recycle cleanup.
- [x] Local tests, independent review và self-test còn đúng candidate; source hashes khớp `9/9` snapshot đã review.
- [x] Canonical ledger `local-artifacts/pr07/` không có unresolved attempt; không dùng directory khác để né guard.
- [x] Operator xác nhận Personal account, temporary permission/secret và kế hoạch trả về baseline; không sửa PR-05 secret/read-only quyền sẵn có.
- [x] Không có callback listener cũ/process live còn chạy; secrets chỉ trong memory/process environment, không command args/file/chat.

Sau approval, cấu hình tạm được chuẩn bị và repository controller được gọi một lần. Fresh failure
đã dừng trước stale; không có retry. Không có live command kèm credential trong plan này.

Closeout bắt buộc dù run fail: best-effort fixture/session cleanup; xác minh artifact+ordered journal và process exit; đóng callback listener; xóa environment/clipboard liên quan; operator xác minh xóa temporary Entra secret và configured permission, giữ baseline PR-05. Báo riêng điều gì controller chứng minh và điều gì operator xác nhận. Cleanup chưa rõ thì ledger giữ UNKNOWN và không chạy lần mới.

## 12. Sau C2: ADR, runtime và đường dừng

Nếu có safe observation, lập đề nghị amendment chứ không sửa accepted ADR ngầm. Amendment phải gọi tên đủ bốn thay đổi:

1. D6: không còn bắt buộc `deferCommit:true` cho mechanism được chọn.
2. D6: final fragment là commit boundary; thay yêu cầu final request mang `If-Match` bằng session-bound concurrency semantics có bằng chứng/authority thích hợp.
3. Giữ precommit reread, immutable item identity, no overwrite, conflict `fail` và rule stale failure; bất kỳ thay đổi accepted HTTP nào phải được giải thích và duyệt riêng, không retroactively đổi kết quả C2_AUTO_V1.
4. D7/recovery: durable intent phải tồn tại trước final fragment; mất response vẫn phải reconcile, không coi upload hoàn tất đồng nghĩa đã finalize DB/lineage.

Đồng bộ PR-07 contract phần provider commit/acceptance/stop condition và acceptance matrix trong một task architecture được duyệt. Trước khi mở runtime cần đánh giá thêm tính bảo đảm của provider: một run safe chưa chứng minh mọi case; nếu Microsoft chưa có documented guarantee, cần xác nhận hoặc kế hoạch verification/risk decision rõ ràng, không tự chấp nhận residual risk.

Nếu confirmed unsafe: loại C2_AUTO_V1, giữ artifact, chuyển câu hỏi cho Microsoft/research về mechanism có thể đảm bảo invariant. Không tự chuyển path/name, `/content`, `replace`/`rename`, OneDrive Business hoặc SharePoint. Nếu inconclusive: chỉ báo boundary/thông tin thiếu và đề xuất bước nghiên cứu tiếp; không ghi “provider impossible”.

Rollback local nếu candidate bị loại là ngừng dùng candidate, giữ bằng chứng và thực hiện targeted revert của thay đổi thuộc task khi được yêu cầu. Không reset worktree, xóa ledger hoặc khôi phục C1 live để thử tiếp. Không có DB migration/runtime activation trong slice này nên không có rollback dữ liệu sản phẩm.

## 13. Trạng thái thực hiện và handoff

- [x] Đối chiếu research với baseline code, accepted contract và primary references.
- [x] Lập scope, protocol, diagnostics, evidence/cleanup design, test matrix và approval gates.
- [x] Product Owner duyệt implementation local.
- [x] WP0–WP5 thực hiện; focused tests, static checks và no-network self-test đạt.
- [x] WP6 independent implementation review mới trên exact corrected diff/hashes.
- [x] WP7 local handoff cập nhật; không live, không commit/push.
- [x] Fresh action-time approval và đúng một C2 live attempt; kết quả `INCONCLUSIVE`, không retry.
- [x] G3 architecture decision: Product Owner duyệt Option A ngày 2026-09-19; giữ D6 và đóng C2
      research, không chấp nhận candidate cho production.
- [ ] PR-07 runtime được mở gate.

**Correction checkpoint:** independent review đầu tiên tìm thấy đúng sáu P2: session closure bị
suy từ destination bytes, ordering v2 chưa khóa create/cancel, post-read có thể bị marker failure
bỏ qua, delete-by-name hợp lệ chưa resolve, predicate PASS lệch giữa validators, và OAuth state test
chưa chứng minh zero redemption. Vòng correction được Product Owner duyệt đã thêm regression vectors
cho cả sáu và sửa fail-closed tương ứng. Không mở rộng sang G2–G4.

Independent review tiếp theo xác minh đủ chín source hashes nhưng tìm thấy một P2 mới: Node
`Date.parse()` chấp nhận date-only và timestamp không timezone trong khi hai Python validators yêu
cầu timezone-aware ISO timestamp. Product Owner đã duyệt đúng một vòng correction + independent
review mới cho finding này. Correction thêm hai regression vectors dùng chung và yêu cầu timezone
suffix tại Node boundary; không nới hai Python validators hoặc refactor ngoài phạm vi.

**Verification local:** `54/54` focused tests PASS; Ruff PASS; `py_compile` PASS; Node
`--check` PASS; `git diff --check` PASS. Controller → Node → probe self-test thật PASS với
`network=NOT_ATTEMPTED`, candidate `C2_AUTO_V1`, schema `2`. Không chạy OAuth/Entra/Graph, không
đổi ADR, không commit/push. Backend gate rộng đi qua `870 passed, 50 skipped` rồi dừng đúng lỗi
infrastructure đã biết vì MinIO local tại `localhost:9000` không chạy trong vòng correction trước;
không rerun gate rộng cho correction Node/test-only này. Component hashes của corrected checkpoint:
controller
`bb3ff05235e9af4bbdae0976e5b02e9103259da4b3f06a14a6e2cc094296ba5a`, launcher
`3be52c56e60fb407c4a18081db3c5bdcd8a3473cea5bf228ad19c04667656602`, probe
`c6f3f22807c509417bd0b07ae070366f474bddb5a77aba5ae7b28e39170aa850`.

**Independent review:** DeepSeek V4.1 Flash xác minh branch/HEAD và `9/9` SHA-256 của exact
`checked_at`-corrected snapshot, kiểm trực tiếp ba timestamp vectors, hai Python validators, Node
validator, tests và doc claims; không tìm thấy P0–P3 và trả `READY`. Reviewer không sửa/tạo file và
không chạy OAuth/Entra/Graph/provider/live/network action.

**G2 live observation:** Product Owner duyệt ngoại lệ nghiên cứu C2 và đúng một invocation
`C2_AUTO_V1` trên snapshot đã review. Attempt `af114cc0-4a10-46eb-ba60-108facc7daa0` chạy tại HEAD
`46e0792b3ae697158f0fe38db8100fbd4afdc6fc`; controller/launcher/probe hashes vẫn lần lượt là
`bb3ff05235e9af4bbdae0976e5b02e9103259da4b3f06a14a6e2cc094296ba5a`,
`3be52c56e60fb407c4a18081db3c5bdcd8a3473cea5bf228ad19c04667656602` và
`c6f3f22807c509417bd0b07ae070366f474bddb5a77aba5ae7b28e39170aa850`.

OAuth đạt. Probe tạo isolated fixture, mở fresh exact-item upload session và gửi partial fragment đầu.
Phản hồi partial không thỏa predicate chính xác `202` với `nextExpectedRanges=["327680-"]`; coherent
post-read vẫn chứng minh destination bytes/eTag được giữ nguyên (`fresh_partial_preserved=true`). Probe
fail closed trước final fragment, concurrent write và stale branch. Sanitized report có
`checked_at=2026-09-18T15:32:18.893562+00:00`, `outcome=INCONCLUSIVE`,
`reason_code=FINAL_NOT_COMPLETED`, `fresh_final_http_status=null`, `runtime_gate=BLOCKED` và
`failure_code=PROBE_REPORTED_FAILURE`. Không retry.

Probe hủy fresh session và đưa fixture vào recycle bin; `cleanup=DELETED_TO_RECYCLE_BIN`,
`cleanup_issue=NONE`. Controller kết thúc không còn sensitive env, callback listener cổng `8000`
hoặc clipboard secret. Product Owner xóa secret tạm và delegated `Files.ReadWrite`; ảnh và kiểm tra
read-only trên Entra sau đó xác nhận chỉ còn secret PR05 và delegated `Files.Read`.

**Gate tiếp theo:** G3 đã đóng theo Option A. D6 giữ nguyên; `runtime_gate=BLOCKED`; không mở G4,
runtime, migrations hoặc PR-08. Chỉ provider clarification read-only được tiếp tục theo plan riêng;
không retry hoặc tái sử dụng authority của candidate đã tiêu thụ.
