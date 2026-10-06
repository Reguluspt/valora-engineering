import { useEffect, useState } from "react";
import { Button, Field, Select } from "@fluentui/react-components";
import { request } from "../../../api/client";
import type { ProjectSummary } from "../../../api/projects";
import { fetchProjectAssetLines, type ProjectAssetLineResponse } from "../../../api/assetLines";
import { evidenceError } from "./usePriceEvidence";

export function HistoricalSourceSelector({ projectId, selectedProject, selectedLine, onProject, onLine }: {
  projectId: string; selectedProject: string; selectedLine: string; onProject: (id: string) => void; onLine: (id: string) => void;
}) {
  const [projects, setProjects] = useState<ProjectSummary[]>([]), [page, setPage] = useState(1);
  const [lines, setLines] = useState<ProjectAssetLineResponse[]>([]), [offset, setOffset] = useState(0);
  const [moreProjects, setMoreProjects] = useState(false), [moreLines, setMoreLines] = useState(false);
  const [loading, setLoading] = useState(false), [error, setError] = useState(""), [reload, setReload] = useState(0);
  useEffect(() => {
    let live = true; setLoading(true); setError("");
    void request<ProjectSummary[]>(`/api/v1/projects?page=${page}&page_size=50`).then(result => {
      if (!live) return;
      setProjects(prior => page === 1 ? result.filter(p => p.id !== projectId) : [...prior, ...result.filter(p => p.id !== projectId)]);
      setMoreProjects(result.length === 50);
    }).catch(caught => { if (live) setError(evidenceError(caught.status)); }).finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [projectId, page, reload]);
  useEffect(() => {
    if (!selectedProject) { setLines([]); return; }
    let live = true; setLoading(true); setError("");
    void fetchProjectAssetLines(selectedProject, { limit: 50, offset }).then(result => {
      if (!live) return;
      if (result.project_id !== selectedProject) throw new Error("Scope mismatch");
      setLines(prior => offset === 0 ? result.items : [...prior, ...result.items]); setMoreLines(result.offset + result.items.length < result.total);
    }).catch(caught => { if (live) setError(evidenceError(caught.status)); }).finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [selectedProject, offset, reload]);
  return <>
    <p>Chọn hồ sơ và tài sản nguồn. Ngày, giá trị và trích đoạn kết quả dưới đây do người dùng ghi lại từ kết quả thẩm định trước.</p>
    {error && <p role="alert">{error} <Button onClick={() => setReload(n => n + 1)}>Tải lại danh sách</Button></p>}
    {loading && <p role="status">Đang tải danh sách nguồn…</p>}
    <Field label="Hồ sơ thẩm định trước" required><Select required value={selectedProject} disabled={loading || Boolean(error)}
      onChange={(_, data) => { onProject(data.value); onLine(""); setLines([]); setOffset(0); }}>
      <option value="">Chọn hồ sơ</option>{projects.map(p => <option key={p.id} value={p.id}>{p.code} · {p.name}</option>)}
    </Select></Field>
    {moreProjects && <Button disabled={loading} onClick={() => setPage(n => n + 1)}>Tải thêm hồ sơ</Button>}
    <Field label="Tài sản trong hồ sơ trước" required><Select required value={selectedLine} disabled={!selectedProject || loading || Boolean(error)}
      onChange={(_, data) => onLine(data.value)}>
      <option value="">Chọn tài sản nguồn</option>{lines.map(l => <option key={l.id} value={l.id}>{l.asset_name}</option>)}
    </Select></Field>
    {moreLines && <Button disabled={loading} onClick={() => setOffset(lines.length)}>Tải thêm tài sản nguồn</Button>}
  </>;
}
