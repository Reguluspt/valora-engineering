# VALORA v2.3 — User Flow Mindmap

**Trạng thái:** `DESIGN SUPPORT / FLOW MAP`
**Authority:** Bám theo handoff v2.3 + các addendum mới nhất. Nếu mâu thuẫn, business/design authority mới nhất thắng.

**2026-11-28:** [Successor v1.2](../plan/VALORA_252_SUCCESSOR_ADR_DRAFT_v1.2.md) và [OFFICIAL-CASE-PROFILE](VALORA_OFFICIAL_CASE_PROFILE_CONTRACT_V1.md) giải thích thiết kế đích. [CODEX](../../CODEX.md#price-evidence-and-supplier-quotes-certified-scope-vs-approved-design) giữ cap SUPPLIER_QUOTES v1.

```mermaid
mindmap
  root((VALORA\nSingle-user Workflow))
    Pre-case
      Trang chủ
      Quản lý yêu cầu sơ bộ
      Tạo yêu cầu sơ bộ
      Upload & Mapping Excel
      Phân tích danh mục
        Kho tri thức
          Gợi ý candidate
          Không phải nguồn giá ưu tiên độc lập
        Nguồn giá/chứng cứ ưu tiên
          1. Giá khảo sát Internet
          2. Thuyết minh đơn giá
          3. Giá Kết quả hồ sơ cũ
        Người dùng ấn định / điều chỉnh giá
      Rà soát tích hợp
      Tạo file kết quả sơ bộ
      Chuyển sang thẩm định chính thức
    Hồ sơ chính thức
      S09 cùng Project và Customer đã bind
        Dữ liệu Profile tùy chọn
      S10 Tổng quan hồ sơ
        Xem và bổ sung Profile theo quyền
      Xác nhận & điều chỉnh danh mục triển khai
      Workbench tài sản
        Asset Context Drawer
          Raw vs Normalized
          Thông số kỹ thuật
          Nguồn giá & Chứng cứ
          Lịch sử
      Nguồn giá & Chứng cứ
        1. Giá khảo sát Internet
        2. Thuyết minh đơn giá
        3. Giá trong Kết quả hồ sơ cũ
        Đối sánh Kho tri thức và chọn nguồn độc lập
        Xác nhận công việc nguồn và đơn giá TĐG
    NCCQ sau xác nhận nguồn và đơn giá
      Một bảng mỗi nhóm báo giá
        Đúng ba NCC cố định cho mọi dòng trong nhóm
        STT bất biến
      Dùng lại kết quả đối sánh từ bước nguồn
        Giá lịch sử khớp đúng NCC là tham chiếu nháp
        Tài sản mới hoặc đổi giá dùng đề xuất nội bộ
          Một giá bằng P
          Hai mục tiêu 105% và 110% theo quantum
          Giới hạn 115% P chỉ cho đề xuất nội bộ
      Báo giá thật theo NCC
        Word theo mẫu và lưu đúng bản gửi
        Nhận phản hồi hoặc file ký và giữ lineage
        Xác nhận đồng ý thật một thao tác theo revision
        S17 chi tiết hoặc ngoại lệ khi cần
      SUPPLIER_SELECTION do server derive từ ba slot hiện hành
    Kết quả thẩm định giá
      Đơn giá TĐG độc lập với báo giá NCC
      Một lần Xác nhận hoàn thành hồ sơ tại APPRAISAL_RESULT
        Chấp nhận exact nguồn độc lập và bind coverage thủ tục riêng
      Bảng 1
        Đặc điểm kinh tế - kỹ thuật
        Immutable layout
      Bảng 2
        Một bảng mỗi nhóm với ba giá NCC thật đã xác nhận
        Không có Thành tiền NCC
      Bảng 3
        Kết quả thẩm định giá
        Đơn giá do người dùng quyết định
        Tổng cộng / Làm tròn / Bằng chữ
    Không gian tài liệu
      Tạo / quản lý bộ tài liệu hồ sơ
      GeneratedDocumentCandidate
      Xác nhận phiên bản mới
      Document Revision
      Microsoft 365 integration
        Mở trong Word
        Return / Auto Revalidation
        DocumentChangeCandidate
        Rà soát thay đổi tài liệu
        Human Commit
      So sánh
      Phát hành bộ tài liệu
      Không có Xuất PDF trong baseline
      Cấu trúc thư mục
        01_Hồ sơ gốc
        02_Tài liệu thẩm định
        03_Hợp đồng
        04_Báo giá nhà cung cấp
        05_Pháp lý
```

## 16 stage canonical

~~~~text
PRELIMINARY_REQUEST → PRELIMINARY_ANALYSIS → PRELIMINARY_READY → OFFICIAL_INTAKE
→ ASSET_REVIEW → ASSET_WORKBENCH → PRICE_EVIDENCE → SUPPLIER_QUOTES
→ SUPPLIER_SELECTION → APPRAISAL_RESULT → DOCUMENT_WORKSPACE → DOCUMENT_SYNC_REVIEW
→ PUBLISHING_PREPARATION → PUBLISHING_EXCEPTION_REVIEW → PUBLISHING_CONFIRMATION → PUBLISHED
~~~~

OFFICIAL_INTAKE giữ cùng Project. Case Overview là orchestration hub, với Profile phục vụ S09/S10 và từng document consumer. S11 chuẩn bị phạm vi tài sản và S12 hoàn thiện KTKT theo exact seal. DOC-Q có thể phục vụ NCCQ theo quyền hẹp riêng. Kho tri thức giúp tìm nguồn và tái sử dụng giá NCC đã xác nhận theo exact revision, giữ history và review.

## Semantic giá

```text
Nguồn ưu tiên xác định giá:
Giá khảo sát Internet
→ Thuyết minh đơn giá
→ Giá trong phần Kết quả của hồ sơ cũ
→ Người dùng quyết định Đơn giá hiện hành / Đơn giá Kết quả

Luồng báo giá NCC đích:
Xác nhận công việc nguồn và đơn giá TĐG → chuẩn bị dự thảo theo nhóm
→ ghi nhận phản hồi thật theo đúng NCC và revision → binding checkpoint do server derive
→ chốt một lần tại Kết quả thẩm định giá → dữ liệu cho tài liệu theo nhóm
Giá đề xuất nội bộ chỉ dùng để chuẩn bị yêu cầu. Báo giá NCC chỉ dùng cho thủ tục và báo cáo.
Nguồn giá độc lập đủ điều kiện chỉ được chấp nhận khi xác nhận hoàn thành hồ sơ.
```

## Working Change Observation / Revision flow

```text
Accepted Revision N
→ Create Working copy
→ user edits/saves in Word
→ automatic provider observation or focus/freshness fallback
→ revalidation + verified read
→ DocumentChangeCandidate
→ Old / V / W
→ recommendation / conflict review
→ explicit human-confirmed command
→ Revision N+1
```

This flow belongs under `DOCUMENT_WORKSPACE → DOCUMENT_SYNC_REVIEW`; it does not add a 17th
canonical case stage. Word Save/provider notification never creates a revision by itself.

## Guardrail

- `Kho tri thức` chỉ gợi ý; không tự ra quyết định giá.
- Giá NCC chỉ phục vụ thủ tục và báo cáo. Nguồn/chứng cứ và đơn giá TĐG có thẩm quyền độc lập.
- Giá NCC lịch sử phục vụ tái tạo báo giá và lineage.
- Người dùng kiểm soát `Đơn giá hiện hành`; mọi thay đổi có history/lineage/audit.
- Không có S14 xác nhận lại giá, màn Kiểm tra hồ sơ riêng hoặc workflow KSCL riêng.
- Kết quả đọc exact group-slot binding từ báo giá thật hiện hành.
- Ba bảng Kết quả thẩm định giá là immutable layout.
- Microsoft 365 quản lý external Working/file/version surface; VALORA quản lý structured business data, snapshots, accepted DocumentRevision/CurrentHead, lineage và audit. OneDrive state never selects authoritative current revision.
