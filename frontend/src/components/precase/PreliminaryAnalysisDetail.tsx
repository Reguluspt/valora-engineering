import React, { type Ref } from "react";
import { Button, Checkbox, Input } from "@fluentui/react-components";

import type { ProjectAssetImportStagingRowResponse } from "../../api/assetImports";
import { StatusBadge } from "../common/StatusBadge";
import type { AnalysisDraft } from "./analysisReviewModel";

export function displayAnalysisNumber(value: string): string {
  if (!value.trim()) return "Chưa nhập";
  const numeric = Number(value);
  return Number.isFinite(numeric) ? new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 10 }).format(numeric) : value;
}

export function AnalysisLineStatus({ line, completed = false }: { line: AnalysisDraft; completed?: boolean }) {
  if (line.has_unresolved_blocking_line) return <StatusBadge status="blocking" label="Còn vướng mắc" />;
  if (completed || line.human_line_confirmed) return <StatusBadge status="approved" label="Đã xác nhận" />;
  return <StatusBadge status="review" label="Chưa xác nhận" />;
}

export function PreliminaryAnalysisDetail({ line, source, completed, disabled, headingRef, outsidePage,
  onChange, onBack, onReveal }: {
  line: AnalysisDraft;
  source?: ProjectAssetImportStagingRowResponse;
  completed: boolean;
  disabled: boolean;
  headingRef: Ref<HTMLHeadingElement>;
  outsidePage: boolean;
  onChange: (patch: Partial<AnalysisDraft>) => void;
  onBack: () => void;
  onReveal: () => void;
}) {
  const rowNumber = line.source_row_number;
  return <aside className="valora-panel precase-analysis-detail" aria-labelledby="analysis-detail-heading"
    onKeyDown={(event) => { if (event.key === "Escape") onBack(); }}>
    <div className="precase-analysis-detail__header">
      <Button className="precase-analysis-detail__back" appearance="subtle" onClick={onBack}>← Về bảng danh mục</Button>
      <div className="precase-analysis-detail__eyebrow">Chi tiết dòng nguồn {rowNumber}</div>
      <h2 id="analysis-detail-heading" ref={headingRef} tabIndex={-1}>{line.identity || "Chưa có nhận diện"}</h2>
      <AnalysisLineStatus line={line} completed={completed} />
    </div>
    <div className="precase-analysis-detail__body">
      {outsidePage && <div className="precase-analysis-detail__selection-note">
        <span>Dòng đang chọn nằm ngoài trang đang hiển thị.</span>
        <Button appearance="transparent" size="small" onClick={onReveal}>Hiển thị dòng đang chọn</Button>
      </div>}
      {completed ? <section className="precase-analysis-detail__pricing" aria-label="Giá đã chốt">
        <div className="precase-analysis-detail__price-read"><span>Đơn giá đề xuất</span><strong>{displayAnalysisNumber(line.proposed_unit_price)}</strong></div>
        <dl className="precase-analysis-detail__facts">
          <div><dt>Giá tham chiếu đã xác nhận</dt><dd>{displayAnalysisNumber(line.confirmed_reference_price)}</dd></div>
          <div><dt>Vận chuyển</dt><dd>{displayAnalysisNumber(line.transport_percentage)}%</dd></div>
          <div className="precase-analysis-detail__full"><dt>Cơ sở giá được chấp nhận</dt><dd>{line.accepted_price_basis || "Không có trong bản đã chốt"}</dd></div>
        </dl>
        <p className="precase-analysis-detail__hint">Bản phân tích đã chốt chỉ cho phép xem.</p>
      </section> : <section className="precase-analysis-detail__pricing" aria-label="Nhập và rà soát giá">
        <label className="precase-analysis-detail__field precase-analysis-detail__price">
          <span>Đơn giá đề xuất</span>
          <Input aria-label={"Đơn giá đề xuất dòng " + rowNumber} disabled={disabled} inputMode="decimal"
            name="proposed_unit_price" value={line.proposed_unit_price} placeholder="Chưa nhập"
            onChange={(_, data) => onChange({ proposed_unit_price: data.value })} />
        </label>
        <div className="precase-analysis-detail__pair">
          <label className="precase-analysis-detail__field"><span>Giá tham chiếu đã xác nhận</span>
            <Input aria-label={"Giá tham chiếu dòng " + rowNumber} disabled={disabled} inputMode="decimal"
              name="confirmed_reference_price" value={line.confirmed_reference_price} placeholder="Chưa nhập"
              onChange={(_, data) => onChange({ confirmed_reference_price: data.value })} />
          </label>
          <label className="precase-analysis-detail__field"><span>Vận chuyển %</span>
            <Input aria-label={"Vận chuyển dòng " + rowNumber} disabled={disabled} inputMode="decimal"
              name="transport_percentage" value={line.transport_percentage} placeholder="Chưa nhập"
              onChange={(_, data) => onChange({ transport_percentage: data.value })} />
          </label>
        </div>
        <label className="precase-analysis-detail__field"><span>Cơ sở giá được chấp nhận</span>
          <Input aria-label={"Cơ sở giá dòng " + rowNumber} disabled={disabled} maxLength={64}
            name="accepted_price_basis" value={line.accepted_price_basis} placeholder="Nhập cơ sở giá đã kiểm tra"
            onChange={(_, data) => onChange({ accepted_price_basis: data.value })} />
        </label>
        <p className="precase-analysis-detail__hint">Đơn giá đề xuất do người dùng nhập; thay đổi giá tham chiếu hoặc vận chuyển không tự ghi đè giá này.</p>
      </section>}
      {!completed && <section className="precase-analysis-detail__section" aria-label="Xác nhận từng dòng">
        <Checkbox aria-label={"Vướng mắc dòng " + rowNumber} label="Còn vướng mắc cần xử lý"
          name="has_unresolved_blocking_line" checked={line.has_unresolved_blocking_line} disabled={disabled}
          onChange={(_, data) => onChange({ has_unresolved_blocking_line: data.checked === true })} />
        <Checkbox aria-label={"Xác nhận rà soát dòng " + rowNumber} label="Tôi đã rà soát và xác nhận dòng này"
          name="human_line_confirmed" checked={line.human_line_confirmed} disabled={disabled || line.has_unresolved_blocking_line}
          onChange={(_, data) => onChange({ human_line_confirmed: data.checked === true })} />
        <p className="precase-analysis-detail__hint">Thay đổi nội dung sẽ bỏ xác nhận của dòng để rà soát lại.</p>
      </section>}
      <section className="precase-analysis-detail__section" aria-label="Thông tin dòng nguồn">
        <h3>Thông tin dòng nguồn</h3>
        {!completed && <label className="precase-analysis-detail__field"><span>Nhận diện</span>
          <Input aria-label={"Nhận diện dòng " + rowNumber} disabled={disabled} maxLength={255}
            name="identity" value={line.identity} onChange={(_, data) => onChange({ identity: data.value })} />
        </label>}
        <dl className="precase-analysis-detail__facts">
          <div><dt>Dòng nguồn</dt><dd>{rowNumber}</dd></div>
          <div><dt>Số lượng nguồn</dt><dd>{line.quantity || "Thiếu"}</dd></div>
          {!completed && <>
            <div><dt>Đơn vị tính</dt><dd>{source?.proposed_unit || "Chưa có dữ liệu"}</dd></div>
            <div><dt>Giá khách hàng (nguồn)</dt><dd>{source?.proposed_raw_price || "Chưa có dữ liệu"}{source?.proposed_currency ? ` ${source.proposed_currency}` : ""}</dd></div>
            <div className="precase-analysis-detail__full"><dt>Mô tả từ nguồn hiện hành</dt><dd>{source?.proposed_description || "Chưa có mô tả trong dữ liệu nguồn"}</dd></div>
          </>}
        </dl>
        {!completed && <p className="precase-analysis-detail__hint">Số lượng nguồn chỉ xem; điều chỉnh qua tệp nguồn hoặc ánh xạ.</p>}
        {completed && <p className="precase-analysis-detail__hint">Bản đã chốt không lưu mô tả, đơn vị tính và giá khách hàng của dòng nguồn.</p>}
      </section>
    </div>
  </aside>;
}
