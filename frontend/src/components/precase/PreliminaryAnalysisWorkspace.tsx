import React, { useEffect, useMemo, useRef, useState } from "react";
import { Button, Input, Select, Textarea } from "@fluentui/react-components";

import type { ProjectAssetImportStagingRowResponse } from "../../api/assetImports";
import type { PreliminaryAnalysisReadResponse } from "../../api/preliminaryAnalysis";
import type { AnalysisDraft } from "./analysisReviewModel";
import { AnalysisLineStatus, displayAnalysisNumber, PreliminaryAnalysisDetail } from "./PreliminaryAnalysisDetail";
import "./preliminary-analysis-workspace.css";

type ReviewFilter = "all" | "unreviewed" | "blocked" | "confirmed" | "missing-price";
interface PresentationLine { draft: AnalysisDraft; originalIndex: number; source?: ProjectAssetImportStagingRowResponse }

const PAGE_SIZE = 50;

function InlineBasisEditor({ rowNumber, value, disabled, onFocus, onChange }: {
  rowNumber: number;
  value: string;
  disabled: boolean;
  onFocus: () => void;
  onChange: (value: string) => void;
}) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${textarea.scrollHeight}px`;
    }
  }, [value]);
  return <Textarea className="precase-analysis-workspace__inline-editor precase-analysis-workspace__inline-basis"
    textarea={{ ref: textareaRef }} aria-label={`Cơ sở giá dòng ${rowNumber} trong bảng`}
    name={`accepted_price_basis_row_${rowNumber}`} value={value} disabled={disabled} maxLength={64}
    size="small" rows={1} resize="none" placeholder="Nhập cơ sở giá" onFocus={onFocus}
    onChange={(_, data) => onChange(data.value)} />;
}

function matchesFilter(line: AnalysisDraft, filter: ReviewFilter, completed: boolean): boolean {
  if (filter === "blocked") return line.has_unresolved_blocking_line;
  if (filter === "confirmed") return completed || (line.human_line_confirmed && !line.has_unresolved_blocking_line);
  if (filter === "unreviewed") return !completed && (!line.human_line_confirmed || line.has_unresolved_blocking_line);
  if (filter === "missing-price") return !line.proposed_unit_price.trim();
  return true;
}

export function PreliminaryAnalysisWorkspace({ drafts, sourceRows, snapshot, disabled, onUpdateDraft }: {
  drafts: AnalysisDraft[];
  sourceRows: ProjectAssetImportStagingRowResponse[];
  snapshot?: PreliminaryAnalysisReadResponse | null;
  disabled: boolean;
  onUpdateDraft: (index: number, patch: Partial<AnalysisDraft>) => void;
}) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<ReviewFilter>("all");
  const [pageIndex, setPageIndex] = useState(0);
  const [selectedRow, setSelectedRow] = useState<number | null>(null);
  const [editingRow, setEditingRow] = useState<number | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const rowButtons = useRef(new Map<number, HTMLButtonElement | HTMLAnchorElement>());
  const listRef = useRef<HTMLElement>(null);
  const focusDetail = useRef(false);
  const returnFocus = useRef(false);
  const completed = Boolean(snapshot);
  const lines = useMemo<PresentationLine[]>(() => {
    if (snapshot) return snapshot.line_manifest.map((line, originalIndex) => ({
      originalIndex,
      draft: { ...line, identity: line.identity ?? "", accepted_price_basis: line.accepted_price_basis ?? "",
        quantity: String(line.quantity ?? ""), confirmed_reference_price: String(line.confirmed_reference_price ?? ""),
        transport_percentage: String(line.transport_percentage ?? ""), proposed_unit_price: String(line.proposed_unit_price ?? "") },
    }));
    const bySourceRow = new Map(sourceRows.map((row) => [row.source_row_number, row]));
    return drafts.map((draft, originalIndex) => ({ draft, originalIndex, source: bySourceRow.get(draft.source_row_number) }));
  }, [drafts, sourceRows, snapshot]);
  const normalizedQuery = query.trim().toLocaleLowerCase("vi-VN");
  const matchesView = ({ draft, source }: PresentationLine) => matchesFilter(draft, filter, completed) &&
    (!normalizedQuery || [draft.source_row_number, draft.identity, source?.proposed_description, source?.proposed_unit,
      draft.accepted_price_basis].join(" ").toLocaleLowerCase("vi-VN").includes(normalizedQuery));
  // Retain the active row until focus leaves it, even if the edit changes its filter match.
  const filtered = lines.filter((line) => matchesView(line) || line.draft.source_row_number === editingRow);
  const retainingEditedRow = lines.some((line) => line.draft.source_row_number === editingRow && !matchesView(line));
  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPage = Math.min(pageIndex, pageCount - 1);
  const visible = filtered.slice(currentPage * PAGE_SIZE, (currentPage + 1) * PAGE_SIZE);
  const selected = lines.find(({ draft }) => draft.source_row_number === selectedRow) ?? lines[0];
  const selectedNumber = selected?.draft.source_row_number;
  const outsidePage = Boolean(selected && !visible.some(({ draft }) => draft.source_row_number === selectedNumber));

  useEffect(() => {
    if (focusDetail.current) {
      headingRef.current?.focus();
      focusDetail.current = false;
    } else if (returnFocus.current && selectedNumber !== undefined) {
      (rowButtons.current.get(selectedNumber) ?? listRef.current)?.focus();
      returnFocus.current = false;
    }
  });

  const openDetail = (rowNumber: number) => {
    if (detailOpen && selectedNumber === rowNumber) {
      headingRef.current?.focus();
      return;
    }
    focusDetail.current = true;
    setSelectedRow(rowNumber);
    setDetailOpen(true);
  };
  const closeDetail = () => {
    returnFocus.current = detailOpen;
    if (!detailOpen && selectedNumber !== undefined) (rowButtons.current.get(selectedNumber) ?? listRef.current)?.focus();
    setDetailOpen(false);
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

  return <div className={`precase-analysis-workspace${detailOpen ? " is-detail-open" : ""}`}>
    <section className="valora-panel precase-analysis-workspace__list" aria-label="Danh mục phân tích" ref={listRef} tabIndex={-1}>
      <div className="precase-analysis-workspace__toolbar">
        <Input aria-label="Tìm trong danh mục phân tích" type="search" className="precase-analysis-workspace__search"
          placeholder="Tìm nhận diện, mô tả, dòng nguồn…" value={query}
          onChange={(_, data) => { setEditingRow(null); setQuery(data.value); setPageIndex(0); }} />
        <Select aria-label="Lọc trạng thái rà soát" value={filter}
          onChange={(_, data) => { setEditingRow(null); setFilter(data.value as ReviewFilter); setPageIndex(0); }}>
          <option value="all">Tất cả dòng</option><option value="unreviewed">Chưa xác nhận</option>
          <option value="blocked">Còn vướng mắc</option><option value="confirmed">Đã xác nhận</option>
          <option value="missing-price">Chưa nhập giá đề xuất</option>
        </Select>
      </div>
      <div className="precase-analysis-workspace__context">
        <span role="status">{filtered.length}/{lines.length} dòng{query || filter !== "all" ? " theo bộ lọc" : " trong danh mục"}{retainingEditedRow ? " · giữ dòng đang sửa" : ""}</span>
        <span>{completed ? "Chọn nhận diện để xem chi tiết" : "Sửa giá ngay trong bảng · chọn nhận diện để xem chi tiết"}</span>
        {selectedNumber !== undefined && <Button appearance="subtle" className="precase-analysis-workspace__open-detail"
          onClick={() => openDetail(selectedNumber)}>Xem chi tiết dòng {selectedNumber}</Button>}
      </div>
      {visible.length ? <div className="valora-table-shell precase-analysis-workspace__table" role="region" tabIndex={0}
        data-editable={!completed}
        aria-label="Bảng phân tích danh mục, cuộn ngang để xem các cột giá">
        <table className="valora-table valora-table--multiline">
          <thead><tr>
            <th scope="col">Dòng nguồn</th><th scope="col" className="precase-analysis-workspace__identity">Nhận diện</th>
            {!completed && <th scope="col">ĐVT</th>}<th scope="col" className="precase-analysis-workspace__numeric">Số lượng nguồn</th>
            {!completed && <th scope="col" className="precase-analysis-workspace__numeric">Giá khách hàng (nguồn)</th>}
            <th scope="col" className="precase-analysis-workspace__basis-column">Cơ sở giá được chấp nhận</th><th scope="col" className="precase-analysis-workspace__numeric precase-analysis-workspace__price-column">Giá tham chiếu đã xác nhận</th>
            <th scope="col" className="precase-analysis-workspace__numeric precase-analysis-workspace__transport-column">Vận chuyển %</th>
            <th scope="col" className="precase-analysis-workspace__numeric precase-analysis-workspace__price-column">Đơn giá đề xuất</th><th scope="col">Rà soát</th>
          </tr></thead>
          <tbody>{visible.map(({ draft: line, source, originalIndex }) => <tr key={line.source_row_number} data-row-source={line.source_row_number}
            data-selected={line.source_row_number === selectedNumber ? "true" : "false"}
            onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setEditingRow(null); }}>
            <td>{line.source_row_number}</td>
            <td className="precase-analysis-workspace__identity">
              <Button appearance="transparent" className="precase-analysis-workspace__row-button"
                ref={(node) => { if (node) rowButtons.current.set(line.source_row_number, node); else rowButtons.current.delete(line.source_row_number); }}
                aria-label={`Xem chi tiết dòng ${line.source_row_number}: ${line.identity || "Chưa có nhận diện"}`}
                aria-pressed={line.source_row_number === selectedNumber} onClick={() => openDetail(line.source_row_number)}>
                {line.identity || "Chưa có nhận diện"}
              </Button>
              {!completed && <p className="precase-analysis-workspace__description">{source?.proposed_description || "Chưa có mô tả nguồn"}</p>}
            </td>
            {!completed && <td>{source?.proposed_unit || "—"}</td>}
            <td className="precase-analysis-workspace__numeric" aria-describedby={completed ? undefined : "analysis-source-quantity-note"}>{line.quantity || "Thiếu"}</td>
            {!completed && <td className="precase-analysis-workspace__numeric">{source?.proposed_raw_price || "—"}
              {source?.proposed_currency && <small>{source.proposed_currency}</small>}</td>}
            <td>{completed ? line.accepted_price_basis || "Chưa nhập" : <InlineBasisEditor rowNumber={line.source_row_number}
              value={line.accepted_price_basis} disabled={disabled} onFocus={() => beginInlineEdit(line.source_row_number)}
              onChange={(value) => updateInlineDraft(originalIndex, line.source_row_number, { accepted_price_basis: value })} />}</td>
            <td className="precase-analysis-workspace__numeric">{completed ? displayAnalysisNumber(line.confirmed_reference_price) :
              <Input className="precase-analysis-workspace__inline-editor" aria-label={`Giá tham chiếu dòng ${line.source_row_number} trong bảng`}
                name={`confirmed_reference_price_row_${line.source_row_number}`} value={line.confirmed_reference_price} disabled={disabled}
                size="small" inputMode="decimal" placeholder="Chưa nhập" onFocus={() => beginInlineEdit(line.source_row_number)}
                onChange={(_, data) => updateInlineDraft(originalIndex, line.source_row_number, { confirmed_reference_price: data.value })} />}</td>
            <td className="precase-analysis-workspace__numeric">{completed ? displayAnalysisNumber(line.transport_percentage) :
              <Input className="precase-analysis-workspace__inline-editor" aria-label={`Vận chuyển dòng ${line.source_row_number} trong bảng`}
                name={`transport_percentage_row_${line.source_row_number}`} value={line.transport_percentage} disabled={disabled}
                size="small" inputMode="decimal" placeholder="Chưa nhập" onFocus={() => beginInlineEdit(line.source_row_number)}
                onChange={(_, data) => updateInlineDraft(originalIndex, line.source_row_number, { transport_percentage: data.value })} />}</td>
            <td className="precase-analysis-workspace__numeric precase-analysis-workspace__proposed">{completed ? displayAnalysisNumber(line.proposed_unit_price) :
              <Input className="precase-analysis-workspace__inline-editor" aria-label={`Đơn giá đề xuất dòng ${line.source_row_number} trong bảng`}
                name={`proposed_unit_price_row_${line.source_row_number}`} value={line.proposed_unit_price} disabled={disabled}
                size="small" inputMode="decimal" placeholder="Chưa nhập" onFocus={() => beginInlineEdit(line.source_row_number)}
                onChange={(_, data) => updateInlineDraft(originalIndex, line.source_row_number, { proposed_unit_price: data.value })} />}</td>
            <td><AnalysisLineStatus line={line} completed={completed} /></td>
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
    {selected && <PreliminaryAnalysisDetail line={selected.draft} source={selected.source} completed={completed}
      disabled={disabled} headingRef={headingRef} outsidePage={outsidePage}
      onBack={closeDetail} onReveal={revealSelected}
      onChange={(patch) => { if (!completed && !disabled) onUpdateDraft(selected.originalIndex, patch); }} />}
  </div>;
}
