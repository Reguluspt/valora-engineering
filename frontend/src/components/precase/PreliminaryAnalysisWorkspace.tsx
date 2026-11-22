import React, { useEffect, useMemo, useRef, useState } from "react";
import { Button, Input, Select } from "@fluentui/react-components";

import type { ProjectAssetImportStagingRowResponse } from "../../api/assetImports";
import type { PreliminaryAnalysisReadResponse } from "../../api/preliminaryAnalysis";
import type { AnalysisDraft } from "./analysisReviewModel";
import { AnalysisLineStatus, displayAnalysisNumber, PreliminaryAnalysisDetail } from "./PreliminaryAnalysisDetail";
import { analysisAmount, analysisAssetPresentation, analysisSourcePrice, formatAnalysisNumber, type AnalysisPresentation } from "./analysisPresentation";
import { ShellIcon } from "../layout/ShellIcon";
import { useAnalysisTableLayout } from "./useAnalysisTableLayout";
import { AnalysisNumberInput } from "./AnalysisNumberInput";
import { draftUrlIssue, sourceCountLabel, useAnalysisSourceDrafts, type SourceDraftStorage } from "./analysisSourceDrafts";
import { analysisColumns, useAnalysisColumnWidths } from "./useAnalysisColumnWidths";
import { useTableMousePan } from "./useTableMousePan";
import "./preliminary-analysis-workspace.css";

type ReviewFilter = "all" | "unreviewed" | "blocked" | "confirmed" | "missing-price" | "unviewed" | "comparison";
interface PresentationLine { draft: AnalysisDraft; originalIndex: number; source?: ProjectAssetImportStagingRowResponse }

const PAGE_SIZE = 50;
const DETAIL_OVERLAY_QUERY = "(max-width: 950px)";

function matchesFilter(line: AnalysisDraft, filter: ReviewFilter, completed: boolean): boolean {
  if (filter === "blocked") return line.has_unresolved_blocking_line;
  if (filter === "confirmed") return completed || (line.human_line_confirmed && !line.has_unresolved_blocking_line);
  if (filter === "unreviewed") return !completed && (!line.human_line_confirmed || line.has_unresolved_blocking_line);
  if (filter === "missing-price") return !line.proposed_unit_price.trim();
  return true;
}

export function PreliminaryAnalysisWorkspace({ drafts, sourceRows, snapshot, disabled, onUpdateDraft, presentation, initialDetailOpen = false, onSummary, onViewedCountChange, onReferenceConditionChange, localSourceDrafts = false, sourceDraftStorage }: {
  drafts: AnalysisDraft[];
  sourceRows: ProjectAssetImportStagingRowResponse[];
  snapshot?: PreliminaryAnalysisReadResponse | null;
  disabled: boolean;
  onUpdateDraft: (index: number, patch: Partial<AnalysisDraft>) => void;
  presentation?: AnalysisPresentation;
  initialDetailOpen?: boolean;
  onSummary?: () => void;
  onViewedCountChange?: (count: number) => void;
  onReferenceConditionChange?: (row: number, field: "vat" | "delivery", value: string) => void;
  localSourceDrafts?: boolean;
  sourceDraftStorage?: SourceDraftStorage;
}) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<ReviewFilter>("all");
  const [pageIndex, setPageIndex] = useState(0);
  const [selectedRow, setSelectedRow] = useState<number | null>(null);
  const [editingRow, setEditingRow] = useState<number | null>(null);
  const [narrow, setNarrow] = useState(() => typeof window !== "undefined" && Boolean(window.matchMedia?.(DETAIL_OVERLAY_QUERY).matches));
  const [detailOpen, setDetailOpen] = useState(initialDetailOpen && !narrow);
  const [temporaryDetail, setTemporaryDetail] = useState(false);
  const [detailTab, setDetailTab] = useState("price");
  const [focusOrigin, setFocusOrigin] = useState<"pointer" | "keyboard">("pointer");
  const [viewedRows, setViewedRows] = useState(() => {
    const firstRow = drafts[0] ?? snapshot?.line_manifest[0];
    return new Set(detailOpen && firstRow ? [firstRow.source_row_number] : []);
  });
  const headingRef = useRef<HTMLHeadingElement>(null);
  const rowButtons = useRef(new Map<number, HTMLButtonElement | HTMLAnchorElement>());
  const listRef = useRef<HTMLElement>(null);
  const focusDetail = useRef(false);
  const returnFocus = useRef(false);
  const temporaryTrigger = useRef<HTMLElement | null>(null);
  const normalTrigger = useRef<HTMLElement | null>(null);
  const wasNormalOverlay = useRef(false);
  const beforeMaximize = useRef<{ row: number | null; tab: string } | null>(null);
  const completed = Boolean(snapshot);
  const sources = useAnalysisSourceDrafts(localSourceDrafts && !completed && !disabled, sourceDraftStorage);
  const lines = useMemo<PresentationLine[]>(() => {
    if (snapshot) return snapshot.line_manifest.map((line, originalIndex) => ({
      originalIndex,
      draft: { ...line, identity: line.identity ?? "", accepted_price_basis: line.accepted_price_basis ?? "",
        quantity: String(line.quantity ?? ""), confirmed_reference_price: String(line.confirmed_reference_price ?? ""),
        transport_percentage: String(line.transport_percentage ?? ""), proposed_unit_price: String(line.proposed_unit_price ?? "") },
    }));
    const byId = new Map(sourceRows.map((row) => [row.id, row]));
    const bySourceRow = new Map(sourceRows.map((row) => [row.source_row_number, row]));
    return drafts.map((draft, originalIndex) => ({
      draft, originalIndex,
      source: draft.staging_row_id ? byId.get(draft.staging_row_id) : bySourceRow.get(draft.source_row_number),
    }));
  }, [drafts, sourceRows, snapshot]);
  const normalizedQuery = query.trim().toLocaleLowerCase("vi-VN");
  const isViewed = (row: number) => viewedRows.has(row) || Boolean(presentation?.assets?.[row]?.viewed);
  const matchesView = ({ draft, source }: PresentationLine) => matchesFilter(draft, filter, completed) && (filter !== "unviewed" || !isViewed(draft.source_row_number)) && (filter !== "comparison" || presentation?.assets?.[draft.source_row_number]?.needsComparison) &&
    (!normalizedQuery || [draft.source_row_number, draft.identity, source?.proposed_description, source?.proposed_unit,
      draft.accepted_price_basis, presentation?.assets?.[draft.source_row_number]?.code].join(" ").toLocaleLowerCase("vi-VN").includes(normalizedQuery));
  // Retain the active row until focus leaves it, even if the edit changes its filter match.
  const filtered = lines.filter((line) => matchesView(line) || line.draft.source_row_number === editingRow);
  const retainingEditedRow = lines.some((line) => line.draft.source_row_number === editingRow && !matchesView(line));
  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPage = Math.min(pageIndex, pageCount - 1);
  const visible = filtered.slice(currentPage * PAGE_SIZE, (currentPage + 1) * PAGE_SIZE);
  const { tableRef, availableWidth, widths, width, handleProps, resizing, canReset, reset } = useAnalysisColumnWidths(visible.length > 0);
  const pan = useTableMousePan(tableRef, visible.length > 0);
  const { maximized, workspace, rememberFocus, toggle } = useAnalysisTableLayout(tableRef);
  const panelOpen = maximized ? temporaryDetail : detailOpen;
  const selected = lines.find(({ draft }) => draft.source_row_number === selectedRow) ?? lines[0];
  const selectedNumber = selected?.draft.source_row_number;
  const outsidePage = Boolean(selected && !visible.some(({ draft }) => draft.source_row_number === selectedNumber));
  const normalOverlay = narrow && detailOpen && !maximized && Boolean(selected);
  const modal = normalOverlay || (maximized && temporaryDetail);

  useEffect(() => {
    const media = typeof window !== "undefined" ? window.matchMedia?.(DETAIL_OVERLAY_QUERY) : undefined;
    if (!media) return;
    const update = () => setNarrow(media.matches);
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    const heading = headingRef.current;
    const enteringOverlay = normalOverlay && !wasNormalOverlay.current;
    wasNormalOverlay.current = normalOverlay;
    if (focusDetail.current || (enteringOverlay && heading && !heading.closest("aside")?.contains(document.activeElement))) {
      headingRef.current?.focus({ preventScroll: true });
      focusDetail.current = false;
    } else if (returnFocus.current && selectedNumber !== undefined) {
      const normalOpener = normalTrigger.current;
      const trigger = temporaryTrigger.current ?? (normalOpener?.getClientRects().length ? normalOpener : null);
      (trigger?.isConnected ? trigger : rowButtons.current.get(selectedNumber) ?? listRef.current)?.focus({ preventScroll: true });
      temporaryTrigger.current = null;
      if (!maximized) normalTrigger.current = null;
      returnFocus.current = false;
    }
  });

  const openDetail = (rowNumber: number, keyboard = true, trigger?: HTMLElement) => {
    setFocusOrigin(keyboard ? "keyboard" : "pointer");
    // Keep the active "Chưa xem" result set stable while inspecting rows in the maximized table.
    if (!maximized || filter !== "unviewed") setViewedRows((current) => new Set(current).add(rowNumber));
    if (maximized && !temporaryDetail) temporaryTrigger.current = trigger ?? null;
    if (!maximized && !detailOpen) normalTrigger.current = trigger ?? null;
    if (panelOpen && selectedNumber === rowNumber) {
      headingRef.current?.focus({ preventScroll: true });
      return;
    }
    focusDetail.current = true;
    setSelectedRow(rowNumber);
    if (maximized) setTemporaryDetail(true);
    else setDetailOpen(true);
  };
  const openEvidence = (rowNumber: number, event: React.MouseEvent<HTMLButtonElement>) => {
    setDetailTab("price");
    openDetail(rowNumber, !event?.detail, event?.currentTarget);
  };
  const closeDetail = () => {
    returnFocus.current = panelOpen;
    if (!normalOverlay && !maximized) normalTrigger.current = null;
    if (!panelOpen && selectedNumber !== undefined) (rowButtons.current.get(selectedNumber) ?? listRef.current)?.focus({ preventScroll: true });
    if (maximized) setTemporaryDetail(false);
    else setDetailOpen(false);
  };
  const toggleLayout = (event: React.MouseEvent<HTMLButtonElement>) => {
    if (!maximized) {
      beforeMaximize.current = { row: selectedRow, tab: detailTab };
    } else if (beforeMaximize.current) {
      const { row, tab } = beforeMaximize.current;
      setSelectedRow(row);
      setDetailTab(tab);
      beforeMaximize.current = null;
      temporaryTrigger.current = null;
      setTemporaryDetail(false);
    }
    toggle(event);
  };
  const beginInlineEdit = (rowNumber: number) => {
    if (completed || disabled) return;
    setSelectedRow(rowNumber);
    setEditingRow(rowNumber);
  };
  const updateInlineDraft = (originalIndex: number, rowNumber: number, patch: Partial<AnalysisDraft>) => {
    if (completed || disabled) return;
    beginInlineEdit(rowNumber);
    onUpdateDraft(originalIndex, patch);
  };
  const revealSelected = () => {
    setEditingRow(null);
    setQuery("");
    setFilter("all");
    setPageIndex(Math.floor((selected?.originalIndex ?? 0) / PAGE_SIZE));
  };
  const resetFilters = () => { setEditingRow(null); setQuery(""); setFilter("all"); setPageIndex(0); };
  const viewedCount = lines.filter(({ draft }) => isViewed(draft.source_row_number)).length;
  useEffect(() => { onViewedCountChange?.(viewedCount); }, [viewedCount, onViewedCountChange]);
  const moveSelection = (direction: number, keyboard = true) => {
    const index = lines.findIndex(({ draft }) => draft.source_row_number === selectedNumber);
    const next = lines[index + direction];
    if (next) openDetail(next.draft.source_row_number, keyboard);
  };

  return <div ref={workspace} className={`precase-analysis-workspace${detailOpen && !maximized ? " is-detail-open" : ""}`}
    data-layout={maximized ? "TABLE_MAXIMIZED" : undefined} data-focus-origin={focusOrigin}
    onPointerDownCapture={() => setFocusOrigin("pointer")}
    onKeyDownCapture={(event) => { if (event.key === "Tab") setFocusOrigin("keyboard"); }}>
    <header className="analysis-page-header">
      <div><nav className="analysis-breadcrumb" aria-label="Vị trí trong hồ sơ"><span>Hồ sơ</span><span>›</span><span>{presentation?.projectCode || "Hiện hành"}</span><span>›</span><span>Danh mục</span></nav>
        <h1>Phân tích danh mục</h1><p>{presentation?.catalogName || "Danh mục từ nguồn hiện hành"} · {lines.length} tài sản{presentation?.period ? ` · ${presentation.period}` : ""}</p></div>
      <div className="analysis-header-actions"><Button appearance="secondary" aria-haspopup={narrow ? "dialog" : undefined} onClick={(event) => detailOpen ? closeDetail() : selectedNumber !== undefined && openDetail(selectedNumber, !event?.detail, event?.currentTarget)} icon={<ShellIcon name="sidebar" />}>{detailOpen ? "Ẩn chi tiết" : "Xem chi tiết"}</Button>
        <Button appearance="primary" disabled={!onSummary} onClick={onSummary}>Tổng kết &amp; xuất →</Button></div>
    </header>
    <section className="analysis-metrics" aria-label="Tình trạng rà soát danh mục">
      <Button appearance="transparent" onClick={resetFilters}><strong>{lines.length}</strong><span>Tài sản <br />trong danh mục</span></Button>
      <Button appearance="transparent" onClick={() => { setFilter("unviewed"); setPageIndex(0); }}><strong>{viewedCount}<small>/{lines.length}</small></strong><span>Đã xem <br />chi tiết</span></Button>
      <Button appearance="transparent" onClick={() => { setFilter("missing-price"); setPageIndex(0); }}><strong>{lines.filter(({ draft }) => !draft.proposed_unit_price.trim()).length}</strong><span>Thiếu <br />đơn giá</span></Button>
      <Button appearance="transparent" disabled={!presentation?.assets} title={presentation?.assets ? undefined : "API phân tích chưa cung cấp trạng thái cần đối chiếu"} onClick={() => { setFilter("comparison"); setPageIndex(0); }}><strong>{presentation?.assets ? lines.filter(({ draft }) => presentation.assets?.[draft.source_row_number]?.needsComparison).length : "—"}</strong><span>Cần <br />đối chiếu</span></Button>
      <div className="analysis-review-state"><strong>{completed ? "Bản phân tích đã chốt" : "Đang rà soát danh mục"}</strong><span>Hồ sơ {presentation?.projectCode || "hiện hành"} · {presentation?.catalogName || "Nguồn hiện hành"}</span></div>
    </section>
    <div className="analysis-content-grid">
    <section className="valora-panel precase-analysis-workspace__list" aria-label="Danh mục phân tích" ref={listRef} tabIndex={-1} inert={modal || undefined}>
      <div className="precase-analysis-workspace__toolbar">
        <Input aria-label="Tìm trong danh mục phân tích" type="search" className="precase-analysis-workspace__search" contentBefore={<ShellIcon name="search" />}
          placeholder="Tìm tài sản, model, mã…" value={query}
          onChange={(_, data) => { setEditingRow(null); setQuery(data.value); setPageIndex(0); }} />
        <div className="analysis-table-controls">
          <Select aria-label="Lọc trạng thái rà soát" value={filter}
            onChange={(_, data) => { setEditingRow(null); setFilter(data.value as ReviewFilter); setPageIndex(0); }}>
            <option value="all">Tất cả tài sản</option><option value="unviewed">Chưa xem</option><option value="unreviewed">Chưa xác nhận</option>
            <option value="blocked">Còn vướng mắc</option><option value="confirmed">Đã xác nhận</option>
            <option value="missing-price">Thiếu đơn giá</option>
            {presentation?.assets && <option value="comparison">Cần đối chiếu</option>}
          </Select>
          <Button appearance="subtle" className="analysis-table-action" aria-label="Di chuyển đến các cột giá" icon={<ShellIcon name="compare" />} onClick={() => {
            const table = tableRef.current;
            const price = table?.querySelector<HTMLElement>("[data-price-column]");
            if (table && price) table.scrollTo({ left: price.offsetLeft, behavior: "auto" });
          }} />
          <Button appearance="subtle" className="analysis-table-action analysis-table-layout-toggle" aria-label={maximized ? "Thu gọn bảng" : "Mở rộng bảng"}
            aria-pressed={maximized} icon={<ShellIcon name="expand" />} onPointerDown={rememberFocus} onClick={toggleLayout}>{maximized ? "Thu gọn" : undefined}</Button>
        </div>
      </div>
      <div className="precase-analysis-workspace__context">
        <span role="status">{filtered.length} / {lines.length} tài sản · 13 cột dữ liệu{retainingEditedRow ? " · giữ dòng đang sửa" : ""}</span>
        <span>Chọn một dòng để xem chứng cứ</span>
        <Button appearance="subtle" size="small" className="analysis-reset-widths" disabled={!canReset || resizing} onClick={reset}>Khôi phục độ rộng mặc định</Button>
        {!maximized && selectedNumber !== undefined && <Button appearance="subtle" className="precase-analysis-workspace__open-detail"
          aria-haspopup={narrow ? "dialog" : undefined} onClick={(event) => openDetail(selectedNumber, !event?.detail, event?.currentTarget)}>Xem chi tiết dòng {selectedNumber}</Button>}
      </div>
      {visible.length ? <div className="valora-table-shell precase-analysis-workspace__table" role="region" tabIndex={0} ref={tableRef}
        {...pan} data-editable={!completed} data-resizing={resizing || undefined}
        data-sticky-index={widths[0] + 100 < availableWidth}
        data-sticky-asset={widths[0] + widths[1] + 100 < availableWidth}
        aria-label="Bảng phân tích danh mục, cuộn ngang để xem các cột giá">
        <table className="valora-table valora-table--multiline" style={{ width, "--analysis-index-width": `${widths[0]}px` } as React.CSSProperties}>
          <colgroup>{analysisColumns.map(({ id }, index) => <col key={id} style={{ width: widths[index] }} />)}</colgroup>
          <thead><tr>{analysisColumns.map((column, index) => <th key={column.id} scope="col" data-price-column={column.id === "customer-price" || undefined}>
            <span>{column.label}</span><span className="analysis-column-resize" {...handleProps(column, index)} />
          </th>)}</tr></thead>
          <tbody>{visible.map(({ draft: line, source, originalIndex }) => <tr key={line.source_row_number} data-row-source={line.source_row_number}
            data-selected={line.source_row_number === selectedNumber ? "true" : "false"}
            onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget) && !event.relatedTarget?.closest(".analysis-table-layout-toggle")) setEditingRow(null); }}>
            <td title={`Dòng Excel gốc: ${line.source_row_number}`}>{originalIndex + 1}</td>
            <td className="precase-analysis-workspace__identity">
              <Button appearance="transparent" className="precase-analysis-workspace__row-button"
                ref={(node) => { if (node) rowButtons.current.set(line.source_row_number, node); else rowButtons.current.delete(line.source_row_number); }}
                aria-label={`Xem chi tiết dòng ${line.source_row_number}: ${line.identity || "Chưa có nhận diện"}`}
                aria-haspopup={maximized || narrow ? "dialog" : undefined}
                aria-pressed={line.source_row_number === selectedNumber} onClick={(event) => openDetail(line.source_row_number, !event?.detail, event?.currentTarget)}>
                {line.identity || "Chưa có nhận diện"}
              </Button>
              <span className="analysis-asset-code">{isViewed(line.source_row_number) && <span aria-label="Đã xem">• </span>}{presentation?.assets?.[line.source_row_number]?.code || `Dòng nguồn ${line.source_row_number}`}</span>
            </td>
            <td className="precase-analysis-workspace__description">{source?.proposed_description || (completed ? "Không lưu trong bản đã chốt" : "Chưa có mô tả nguồn")}</td>
            <td className="analysis-cell-centered">{source?.proposed_unit || "—"}</td>
            <td className="precase-analysis-workspace__numeric analysis-cell-centered" aria-describedby={completed ? undefined : "analysis-source-quantity-note"}>{formatAnalysisNumber(line.quantity, "Thiếu")}</td>
            <td className="precase-analysis-workspace__numeric" title={source?.proposed_currency}>{analysisSourcePrice(source)}{source?.proposed_currency && <span className="analysis-sr-only"> {source.proposed_currency}</span>}</td>
            <td className="precase-analysis-workspace__numeric">{presentation?.assets?.[line.source_row_number]?.customerAmount || "—"}</td>
            <td className="precase-analysis-workspace__numeric">{formatAnalysisNumber(presentation?.assets?.[line.source_row_number]?.surveyPrice || "")}</td>
            <td className="precase-analysis-workspace__numeric precase-analysis-workspace__proposed">{completed ? displayAnalysisNumber(line.proposed_unit_price) :
              <AnalysisNumberInput className="precase-analysis-workspace__inline-editor" aria-label={`Đơn giá đề xuất dòng ${line.source_row_number} trong bảng`}
                name={`proposed_unit_price_row_${line.source_row_number}`} value={line.proposed_unit_price} disabled={disabled}
                size="small" inputMode="decimal" placeholder="—" onFocus={() => beginInlineEdit(line.source_row_number)}
                onChange={(value) => updateInlineDraft(originalIndex, line.source_row_number, { proposed_unit_price: value })} />}</td>
            <td className="precase-analysis-workspace__numeric">{analysisAmount(line.proposed_unit_price, line.quantity)}</td>
            <td><Button appearance="transparent" className="analysis-source-count" aria-label={`Xem nguồn giá dòng ${line.source_row_number}`} aria-haspopup={maximized || narrow ? "dialog" : undefined}
              title="Nguồn nháp và gợi ý chưa được đăng ký hoặc xác nhận chính thức" onClick={(event) => openEvidence(line.source_row_number, event)}>
              {localSourceDrafts || presentation?.assets ? sourceCountLabel(sources.byRow[line.source_row_number] || [], Boolean(presentation?.assets?.[line.source_row_number]?.reference)) : "Chưa có dữ liệu"}
            </Button></td>
            <td className="analysis-cell-centered"><Button appearance="transparent" className="analysis-source-count analysis-evidence-target" aria-label={`Xem chứng cứ dòng ${line.source_row_number}`}
              aria-haspopup={maximized || narrow ? "dialog" : undefined} onClick={(event) => openEvidence(line.source_row_number, event)}>
              {localSourceDrafts ? (sources.byRow[line.source_row_number] || []).reduce((count, source) => count + source.images.length + Number(!draftUrlIssue(source.url)), 0) : presentation?.assets?.[line.source_row_number]?.evidenceCount ?? "—"}
            </Button></td>
            <td>{presentation?.assets?.[line.source_row_number] ? <span className={`analysis-status ${presentation.assets[line.source_row_number].statusTone}`}>{presentation.assets[line.source_row_number].status}</span> : <AnalysisLineStatus line={line} completed={completed} />}</td>
          </tr>)}</tbody>
        </table>
      </div> : <div className="precase-analysis-workspace__empty" role="status">
        <strong>Không có dòng phù hợp</strong><p>Thử nhận diện, mô tả hoặc bộ lọc khác.</p>
        <Button appearance="secondary" onClick={resetFilters}>Xóa bộ lọc</Button>
      </div>}
      <div className="precase-analysis-workspace__footer">
        <div className="precase-analysis-workspace__footer-notes">
          <span>{completed ? "Bản đã chốt · chỉ xem" : "Các chỉnh sửa chỉ được chốt sau khi xác nhận"}</span>
          {!completed && <span id="analysis-source-quantity-note">Số lượng nguồn chỉ xem; điều chỉnh qua tệp nguồn hoặc ánh xạ.</span>}
        </div>
        {pageCount > 1 && <div className="precase-analysis-workspace__pagination">
          <Button appearance="subtle" disabled={currentPage === 0} onClick={() => setPageIndex(currentPage - 1)}>Trang trước</Button>
          <span>Trang {currentPage + 1}/{pageCount}</span>
          <Button appearance="subtle" disabled={currentPage + 1 === pageCount} onClick={() => setPageIndex(currentPage + 1)}>Trang sau</Button>
        </div>}
      </div>
    </section>
    {selected && <PreliminaryAnalysisDetail sourceDrafts={sources.byRow[selected.draft.source_row_number] || []} sourceActions={sources} localSourceDrafts={localSourceDrafts} line={selected.draft} source={selected.source} completed={completed} open={panelOpen} modal={modal}
      tab={detailTab} onTabChange={setDetailTab}
      presentation={analysisAssetPresentation(selected.draft, presentation?.assets?.[selected.draft.source_row_number])}
      position={selected.originalIndex} count={lines.length} onPrevious={(keyboard) => moveSelection(-1, keyboard)} onNext={(keyboard) => moveSelection(1, keyboard)}
      onReferenceConditionChange={onReferenceConditionChange ? (field, value) => onReferenceConditionChange(selected.draft.source_row_number, field, value) : undefined}
      disabled={disabled} headingRef={headingRef} outsidePage={outsidePage}
      onBack={closeDetail} onReveal={revealSelected}
      onChange={(patch) => { if (!completed && !disabled) onUpdateDraft(selected.originalIndex, patch); }} />}
    </div>
  </div>;
}
