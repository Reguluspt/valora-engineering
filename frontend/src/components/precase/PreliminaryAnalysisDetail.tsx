import React, { type Ref } from "react";
import { Button, Checkbox, Input, Select, Tab, TabList, useModalAttributes } from "@fluentui/react-components";

import type { ProjectAssetImportStagingRowResponse } from "../../api/assetImports";
import { StatusBadge } from "../common/StatusBadge";
import type { AnalysisDraft } from "./analysisReviewModel";
import { analysisAmount, formatAnalysisNumber, type AnalysisAssetPresentation } from "./analysisPresentation";
import { AnalysisNumberInput } from "./AnalysisNumberInput";
import { AnalysisBasisInput } from "./AnalysisBasisInput";
import { AnalysisSourcesPanel } from "./AnalysisSourcesPanel";
import type { SourceDraft, useAnalysisSourceDrafts } from "./analysisSourceDrafts";

export function displayAnalysisNumber(value: string): string {
  return formatAnalysisNumber(value, "Chưa nhập");
}

export function AnalysisLineStatus({ line, completed = false }: { line: AnalysisDraft; completed?: boolean }) {
  if (line.has_unresolved_blocking_line) return <StatusBadge status="blocking" label="Còn vướng mắc" />;
  if (completed || line.human_line_confirmed) return <StatusBadge status="approved" label="Đã xác nhận" />;
  return <StatusBadge status="review" label="Chưa xác nhận" />;
}

export function PreliminaryAnalysisDetail({ line, source, completed, disabled, headingRef, outsidePage,
  onChange, onBack, onReveal, open, modal, presentation, position, count, onPrevious, onNext, onReferenceConditionChange, sourceDrafts, sourceActions, localSourceDrafts, tab, onTabChange }: {
  sourceDrafts: SourceDraft[];
  sourceActions: ReturnType<typeof useAnalysisSourceDrafts>;
  localSourceDrafts: boolean;
  tab: string;
  onTabChange: (tab: string) => void;
  line: AnalysisDraft;
  source?: ProjectAssetImportStagingRowResponse;
  completed: boolean;
  disabled: boolean;
  headingRef: Ref<HTMLHeadingElement>;
  outsidePage: boolean;
  onChange: (patch: Partial<AnalysisDraft>) => void;
  onBack: () => void;
  onReveal: () => void;
  open: boolean;
  modal: boolean;
  presentation: AnalysisAssetPresentation;
  position: number;
  count: number;
  onPrevious: (keyboard?: boolean) => void;
  onNext: (keyboard?: boolean) => void;
  onReferenceConditionChange?: (field: "vat" | "delivery", value: string) => void;
}) {
  const { modalAttributes } = useModalAttributes({ trapFocus: true, legacyTrapFocus: true });
  const rowNumber = line.source_row_number;
  const reference = presentation.reference;
  const observed = Boolean(presentation.code);
  const field = (label: string, name: "confirmed_reference_price" | "transport_percentage", aria: string) => <label className="analysis-field">
    <span>{label}</span><AnalysisNumberInput key={rowNumber} aria-label={aria + rowNumber} name={name} value={line[name]} disabled={disabled} inputMode="decimal"
      placeholder="Chưa có" onChange={(value) => onChange({ [name]: value })} />
  </label>;

  return <>
    {open && <button type="button" className="analysis-panel-scrim" tabIndex={-1} aria-hidden={modal || undefined} aria-label="Đóng nền chi tiết tài sản" onClick={onBack} />}
    <aside className="valora-panel precase-analysis-detail" hidden={!open} aria-labelledby="analysis-detail-heading"
      role={modal ? "dialog" : undefined} aria-modal={modal || undefined} {...(modal ? modalAttributes : {})}
      onKeyDown={(event) => {
        if (event.key === "Escape" && !event.defaultPrevented && !event.nativeEvent?.isComposing) {
          event.preventDefault?.();
          onBack();
        }
      }}>
      <div className="precase-analysis-detail__header">
        <div className="analysis-panel-eyebrow"><span>{presentation.code || `Dòng nguồn ${rowNumber}`} / TÀI SẢN {String(position + 1).padStart(2, "0")} TRÊN {count}</span>
          <Button appearance="subtle" className="analysis-close" aria-label="Đóng chi tiết tài sản" onClick={onBack}>×</Button></div>
        <h2 id="analysis-detail-heading" ref={headingRef} tabIndex={-1}>{line.identity || "Chưa có nhận diện"}</h2>
        <div className="analysis-panel-badges"><span className={`analysis-status ${presentation.statusTone}`}>{presentation.status}</span><span className="analysis-status gray">Đã xem</span></div>
        <TabList selectedValue={tab} onTabSelect={(_, data) => onTabChange(String(data.value))} aria-label="Nội dung chi tiết tài sản">
          <Tab value="price" id="analysis-tab-price" aria-controls="analysis-panel-body">Giá &amp; chứng cứ</Tab>
          <Tab value="specs" id="analysis-tab-specs" aria-controls="analysis-panel-body">Đặc điểm &amp; SL</Tab>
          <Tab value="history" id="analysis-tab-history" aria-controls="analysis-panel-body">Lịch sử</Tab>
        </TabList>
      </div>
      <div className="precase-analysis-detail__body" id="analysis-panel-body" role="tabpanel" aria-labelledby={`analysis-tab-${tab}`} tabIndex={0}>
        {outsidePage && <div className="precase-analysis-detail__selection-note"><span>Dòng đang chọn nằm ngoài trang đang hiển thị.</span><Button appearance="transparent" size="small" onClick={onReveal}>Hiển thị dòng đang chọn</Button></div>}
        <div hidden={tab !== "price"}>
          <section className="analysis-price-box" aria-label={completed ? "Giá đã chốt" : "Nhập và rà soát giá"}>
            <div className="analysis-price-label"><span>ĐƠN GIÁ ĐỀ XUẤT</span><span>{presentation.manual ? "Nhập tay" : "Theo gợi ý"}</span></div>
            <div className="analysis-price-edit">{completed ? <strong>{displayAnalysisNumber(line.proposed_unit_price)}</strong> :
              <AnalysisNumberInput key={rowNumber} aria-label={"Đơn giá đề xuất dòng " + rowNumber} disabled={disabled} inputMode="decimal"
                name="proposed_unit_price" value={line.proposed_unit_price} placeholder="Nhập đơn giá"
                onChange={(value) => onChange({ proposed_unit_price: value })} />}
              <span>đ / {source?.proposed_unit || "—"}</span></div>
            <div className="analysis-price-total"><span>Số lượng {formatAnalysisNumber(line.quantity)} {source?.proposed_unit}</span><b>{analysisAmount(line.proposed_unit_price, line.quantity)} đ</b></div>
          </section>
          <AnalysisSourcesPanel key={rowNumber} row={rowNumber} reference={reference} drafts={sourceDrafts} actions={sourceActions}
            editable={localSourceDrafts && !completed && !disabled} fixture={localSourceDrafts} />
          {presentation.comparison && <div className="analysis-comparison-note">⚠ <div><strong>{presentation.comparison}</strong><br /><span>Đối chiếu nguồn chưa có trong API phân tích.</span></div></div>}
          <div className="analysis-section-caption">Cơ sở đề xuất <span>Nhân viên quyết định giá</span></div>
          {completed ? <dl className="precase-analysis-detail__facts"><div><dt>Giá tham chiếu đã xác nhận</dt><dd>{displayAnalysisNumber(line.confirmed_reference_price)}</dd></div><div><dt>Vận chuyển</dt><dd>{displayAnalysisNumber(line.transport_percentage)}%</dd></div></dl> :
            <><div className="analysis-field-grid"><label className="analysis-field"><span>Giá khảo sát (đ) · Chỉ đọc</span><output className="analysis-survey-readonly" aria-label="Giá khảo sát" tabIndex={0} title="Chỉ đọc. Có thể chọn và sao chép; API chưa có lệnh lưu giá khảo sát riêng">{formatAnalysisNumber(presentation.surveyPrice || "")}</output></label>{field("Vận chuyển (%)", "transport_percentage", "Vận chuyển dòng ")}</div>
              {field("Giá tham chiếu đã xác nhận (đ)", "confirmed_reference_price", "Giá tham chiếu dòng ")}</>}
          <div className="analysis-formula"><span>Khảo sát + vận chuyển</span><b>{presentation.suggestedPrice ? formatAnalysisNumber(presentation.suggestedPrice) + " đ" : "Chưa có gợi ý từ máy chủ"}</b></div>
          {presentation.manual && <p className="analysis-field-note">Giá nhập tay được giữ độc lập với gợi ý.</p>}
          <div className="analysis-section-caption">Điều kiện nguồn tham khảo <span>{onReferenceConditionChange && reference ? "Chỉ trong phiên xem thử" : "Chỉ đọc"}</span></div>
          <div className="analysis-field-grid">{([["VAT", "vat"], ["Vận chuyển", "delivery"]] as const).map(([label, field]) => <label className="analysis-field" key={field}><span>{label}</span>
            {onReferenceConditionChange && reference ? <Select aria-label={label} value={reference[field]} onChange={(_, data) => onReferenceConditionChange(field, data.value)}><option>Chưa bao gồm</option><option>Đã bao gồm</option><option>Chưa xác định</option></Select>
              : <span className="analysis-condition-readonly" role="note" aria-label={label + " chỉ đọc"} title="API chưa hỗ trợ sửa điều kiện nguồn">{reference?.[field] || "Chưa xác định"}</span>}</label>)}</div>
          <div className="analysis-section-caption">Diễn giải cơ sở đề xuất <span>♧</span></div>
          {completed ? <p>{line.accepted_price_basis || "Không có trong bản đã chốt"}</p> : <label className="analysis-field"><span className="analysis-sr-only">Cơ sở giá được chấp nhận</span>
            <AnalysisBasisInput key={rowNumber} aria-label={"Cơ sở giá dòng " + rowNumber} name="accepted_price_basis" value={line.accepted_price_basis} disabled={disabled} rows={3}
              onChange={(value) => onChange({ accepted_price_basis: value })} /></label>}
          {presentation.note && <p className="analysis-observed-note">{presentation.note}</p>}
          <p className="analysis-field-note">Cơ sở giá tối đa 64 ký tự. Diễn giải, URL và ảnh trong nguồn nháp chưa được lưu hệ thống.</p>
          {!completed && <section className="precase-analysis-detail__section" aria-label="Xác nhận từng dòng">
            <Checkbox aria-label={"Vướng mắc dòng " + rowNumber} label="Còn vướng mắc cần xử lý" name="has_unresolved_blocking_line" checked={line.has_unresolved_blocking_line} disabled={disabled}
              onChange={(_, data) => onChange({ has_unresolved_blocking_line: data.checked === true })} />
            <Checkbox aria-label={"Xác nhận rà soát dòng " + rowNumber} label="Tôi đã rà soát và xác nhận dòng này" name="human_line_confirmed"
              checked={line.human_line_confirmed} disabled={disabled || line.has_unresolved_blocking_line} onChange={(_, data) => onChange({ human_line_confirmed: data.checked === true })} />
            <p className="analysis-field-note">Thay đổi nội dung sẽ bỏ xác nhận của dòng để rà soát lại.</p>
          </section>}
          {completed && <p className="analysis-field-note">Bản phân tích đã chốt chỉ cho phép xem.</p>}
        </div>
        <section hidden={tab !== "specs"} aria-label="Thông tin dòng nguồn">
          <h3 className="analysis-section-caption">Thông tin nhận diện</h3>
          <dl className="analysis-specs">
            <div><dt>Mã tài sản</dt><dd>{presentation.code || "API chưa cung cấp"}</dd></div>
            <div><dt>Tên tài sản</dt><dd>{completed ? line.identity || "Chưa có nhận diện" : <Input aria-label={"Nhận diện dòng " + rowNumber} name="identity" disabled={disabled} maxLength={255} value={line.identity} onChange={(_, data) => onChange({ identity: data.value })} />}</dd></div>
            <div><dt>Dòng Excel gốc</dt><dd>{rowNumber}</dd></div>
          </dl>
          <h3 className="analysis-section-caption">Đặc điểm kỹ thuật</h3>
          <p className="analysis-spec-description">{source?.proposed_description || "Không có trong bản phân tích"}</p>
          <h3 className="analysis-section-caption">Số lượng và đơn giá nguồn</h3>
          <dl className="analysis-specs">
            <div><dt>ĐVT</dt><dd>{source?.proposed_unit || "—"}</dd></div>
            <div><dt>Số lượng nguồn</dt><dd>{formatAnalysisNumber(line.quantity)}</dd></div>
            <div><dt>Đơn giá KH</dt><dd>{source?.proposed_raw_price || "—"}</dd></div>
          </dl>
          <p className="analysis-field-note">{completed ? "Bản đã chốt không lưu mô tả, đơn vị tính và giá khách hàng của dòng nguồn." : "Số lượng nguồn chỉ xem; điều chỉnh qua tệp nguồn hoặc ánh xạ."}</p>
        </section>
        <section hidden={tab !== "history"} aria-label="Lịch sử chỉnh sửa">{presentation.history?.length ? presentation.history.map((entry, index) => <div className="analysis-history-entry" key={index}><p>{entry.text}<small>{entry.time}</small></p></div>) : <div className="analysis-source-empty"><strong>Chưa có lịch sử cho dòng này</strong><p>API phân tích chưa cung cấp lịch sử chỉnh sửa từng dòng.</p></div>}</section>
      </div>
      <footer className="analysis-panel-footer"><span>{observed ? "Đã mở xem chi tiết" : completed ? "Bản đã chốt · chỉ xem" : "Nháp · chưa chốt máy chủ"}</span><div>
        <Button appearance="subtle" aria-label="Tài sản trước" disabled={position === 0} onClick={(event) => onPrevious(!event?.detail)}>‹</Button>
        <Button appearance="primary" disabled={position + 1 >= count} onClick={(event) => onNext(!event?.detail)}>Tiếp theo →</Button>
      </div></footer>
    </aside>
  </>;
}
