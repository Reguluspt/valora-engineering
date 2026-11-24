import { useEffect, useRef, useState, type Dispatch, type SetStateAction } from "react";

export const sourceKinds = {
  internet_survey: "Giá khảo sát Internet",
  unit_price_explanation: "Thuyết minh đơn giá",
  prior_appraisal_result: "Giá kết quả thẩm định của hồ sơ cũ",
};
export const sourceEvaluations = {
  unreviewed: "Chưa đánh giá",
  accepted: "Chấp nhận làm cơ sở",
  review: "Cần đối chiếu thêm",
  excluded: "Loại khỏi cơ sở",
};
export interface SourceDraft {
  id: string;
  kind: keyof typeof sourceKinds;
  title: string;
  origin: string;
  price: string;
  currency: string;
  unit: string;
  capturedAt: string;
  createdAt: number;
  specifications: string;
  vat: string;
  delivery: string;
  narrative: string;
  url: string;
  pendingUrls: string[];
  evaluation: keyof typeof sourceEvaluations;
  needsReview: boolean;
  images: { id: string; url: string; name: string; blob: Blob }[];
  error: string;
}
export function newSourceDraft(url = ""): SourceDraft {
  return { id: crypto.randomUUID(), kind: "internet_survey", title: "", origin: "", price: "", currency: "VND", unit: "", capturedAt: "", createdAt: Date.now(), specifications: "", vat: "Chưa xác định", delivery: "Chưa xác định", narrative: "", url, pendingUrls: [], evaluation: "unreviewed", needsReview: false, images: [], error: "" };
}

export function draftUrlIssue(text: string): "https" | "credentials" | null {
  if (!/^https?:\/\/[^/?#]/i.test(text)) return "https";
  let url: URL;
  try {
    url = new URL(text);
  } catch { return "https"; }
  const credentialKey = /^(?:(?:access|auth|id|refresh|session|bearer|oauth)?token|apikey|authorization|password|passwd|clientsecret|sig|signature|xamzsignature|xgoogsignature)$/i;
  const fragmentParams = new URLSearchParams(url.hash.slice(1).replace(/^[^=&?]*\?/, ""));
  if (url.username || url.password || [url.searchParams, fragmentParams].some(params =>
    Array.from(params.keys()).some(key => credentialKey.test(key.replace(/[-_]/g, ""))),
  )) return "credentials";
  return url.protocol === "https:" && !/[\s\\\u0000-\u001f\u007f]/.test(text) ? null : "https";
}

export function draftUrlTokens(text: string) {
  const tokens = text.matchAll(/(?:^|[\s([{"'“‘<])((?:[a-z][a-z\d+.-]*:\/\/|(?:https?|javascript|data|mailto):|www\.)[^\s<>"“”‘’]*)/gi);
  return [...new Set(Array.from(tokens, ([, token]) => token))];
}

export function sourceHasUrlCredentials({ url, narrative }: Pick<SourceDraft, "url" | "narrative">) {
  return draftUrlIssue(url) === "credentials" || draftUrlTokens(narrative).some(token => draftUrlIssue(token) === "credentials");
}

export type StoredSourceDraft = Omit<SourceDraft, "images" | "pendingUrls" | "error"> & {
  images: Omit<SourceDraft["images"][number], "url">[];
};

export interface SourceDraftStorage {
  scope: string;
  load: () => Promise<{ row: number; version: number; draft: StoredSourceDraft }[]>;
  save: (row: number, draft: StoredSourceDraft, expectedVersion: number) => Promise<{ version: number; verified: boolean }>;
  remove: (row: number, id: string, expectedVersion: number) => Promise<void>;
}

export function canAutosaveSource(source: Pick<SourceDraft, "url" | "price" | "narrative">) {
  const { url, price } = source;
  return !draftUrlIssue(url) && /^\d+(?:\.\d+)?$/.test(price) && Number.isFinite(Number(price)) && Number(price) > 0 && !sourceHasUrlCredentials(source);
}

type DraftRows = Record<number, SourceDraft[]>;
type SaveStatus = "session" | "incomplete" | "saving" | "saved" | "failed";
type SaveJob = { draft: SourceDraft; version: number; timer?: ReturnType<typeof setTimeout>; task: Promise<void>; attempted?: boolean; removing?: boolean };

function toStoredDraft({ images, pendingUrls, error, ...draft }: SourceDraft): StoredSourceDraft {
  return { ...draft, images: images.map(({ id, name, blob }) => ({ id, name, blob })) };
}

function useSourceAutosave(storage: SourceDraftStorage | undefined, byRow: DraftRows, setByRow: Dispatch<SetStateAction<DraftRows>>, resources: Set<string>) {
  const [availability, setAvailability] = useState<"loading" | "ready" | "failed">(storage ? "loading" : "ready");
  const [status, setStatus] = useState<Record<string, SaveStatus>>({});
  const jobs = useRef(new Map<string, SaveJob>()).current;

  const mark = (id: string, next: SaveStatus) => setStatus(current => current[id] === next ? current : { ...current, [id]: next });

  useEffect(() => {
    if (!storage) return;
    let active = true;
    setAvailability("loading");
    storage.load().then(entries => {
      if (!active) return;
      const rows: DraftRows = {};
      const restored: Record<string, SaveStatus> = {};
      for (const { row, version, draft } of entries) {
        const source = { ...draft, pendingUrls: [], error: "", images: draft.images.map(image => {
          const url = URL.createObjectURL(image.blob);
          resources.add(url);
          return { ...image, url };
        }) };
        (rows[row] ??= []).push(source);
        jobs.set(source.id, { draft: source, version, task: Promise.resolve() });
        restored[source.id] = "saved";
      }
      setByRow(rows);
      setStatus(restored);
      setAvailability("ready");
    }).catch(() => { if (active) setAvailability("failed"); });
    return () => {
      active = false;
      jobs.forEach(job => clearTimeout(job.timer));
      jobs.clear();
    };
  }, [storage, jobs, resources, setByRow]);

  useEffect(() => {
    if (!storage || availability === "loading") return;
    for (const [row, sources] of Object.entries(byRow)) {
      for (const source of sources) {
        const job: SaveJob = jobs.get(source.id) ?? { draft: source, version: 0, task: Promise.resolve() };
        if (jobs.has(source.id) && (job.draft === source || job.removing)) continue;
        jobs.set(source.id, job);
        clearTimeout(job.timer);
        job.draft = source;
        if (!canAutosaveSource(source)) {
          mark(source.id, "incomplete");
          continue;
        }
        mark(source.id, "saving");
        job.timer = setTimeout(() => {
          job.task = job.task.then(async () => {
            if (job.draft !== source || job.removing || jobs.get(source.id) !== job) return;
            try {
              job.attempted = true;
              const { version, verified } = await storage.save(Number(row), toStoredDraft(source), job.version);
              job.version = version;
              if (job.draft === source && !job.removing && jobs.get(source.id) === job) mark(source.id, verified ? "saved" : "failed");
            } catch {
              if (job.draft === source && !job.removing && jobs.get(source.id) === job) mark(source.id, "failed");
            }
          });
        }, 800);
      }
    }
  }, [storage, byRow, availability, jobs]);

  const removeStored = async (row: number, id: string) => {
    const job = jobs.get(id);
    if (!storage || !job) return true;
    if (job.removing) return false;
    clearTimeout(job.timer);
    job.removing = true;
    await job.task;
    try {
      if (job.version || job.attempted) await storage.remove(row, id, job.version);
      jobs.delete(id);
      setStatus(current => {
        const next = { ...current };
        delete next[id];
        return next;
      });
      return true;
    } catch {
      job.removing = false;
      mark(id, "failed");
      return false;
    }
  };

  const statusFor = (source: SourceDraft): SaveStatus => {
    if (!storage) return "session";
    if (!canAutosaveSource(source)) return "incomplete";
    return jobs.get(source.id)?.draft === source ? status[source.id] ?? "saving" : "saving";
  };
  return { loading: availability === "loading", unavailable: availability === "failed", statusFor, removeStored };
}

export function useAnalysisSourceDrafts(enabled: boolean, storage?: SourceDraftStorage) {
  const [byRow, setByRow] = useState<DraftRows>({});
  const resources = useRef(new Set<string>());
  const autosave = useSourceAutosave(enabled ? storage : undefined, byRow, setByRow, resources.current);
  useEffect(() => () => { resources.current.forEach(url => URL.revokeObjectURL(url)); resources.current.clear(); }, []);
  const change = (row: number, action: (sources: SourceDraft[]) => SourceDraft[]) => {
    if (enabled) setByRow(current => ({ ...current, [row]: action(current[row] || []) }));
  };
  const add = (row: number, url = "") => change(row, sources => [...sources, newSourceDraft(url)]);
  const patch = (row: number, id: string, values: Partial<SourceDraft>) => change(row, sources => sources.map(source => source.id === id ? {
    ...source, ...values,
    needsReview: values.needsReview ?? (source.needsReview || (source.evaluation !== "unreviewed" && Object.keys(values).some(key => !["evaluation", "error", "pendingUrls"].includes(key)))),
  } : source));
  const remove = (row: number, id: string) => {
    if (!enabled) return;
    const discard = () => {
      (byRow[row] || []).find(source => source.id === id)?.images.forEach(image => { URL.revokeObjectURL(image.url); resources.current.delete(image.url); });
      change(row, sources => sources.filter(source => source.id !== id));
    };
    if (!storage) discard();
    else void autosave.removeStored(row, id).then(removed => { if (removed) discard(); });
  };
  const removeImage = (row: number, source: SourceDraft, id: string) => {
    if (!enabled) return;
    const image = source.images.find(image => image.id === id);
    if (image) { URL.revokeObjectURL(image.url); resources.current.delete(image.url); }
    patch(row, source.id, { images: source.images.filter(image => image.id !== id) });
  };
  const attach = (row: number, source: SourceDraft, files: File[]) => {
    if (!enabled) return;
    const accepted: SourceDraft["images"] = [];
    let error = "";
    for (const file of files) {
      if (!/^image\/(png|jpeg|webp|gif)$/.test(file.type) || file.size === 0 || file.size > 10 * 1024 * 1024) {
        error = "Ảnh xem trước cần là PNG, JPEG, WebP hoặc GIF, dung lượng không quá 10 MiB mỗi ảnh. Ảnh không hợp lệ chưa được thêm.";
        continue;
      }
      const url = URL.createObjectURL(file);
      resources.current.add(url);
      accepted.push({ id: crypto.randomUUID(), url, name: file.name || "Ảnh clipboard", blob: file });
    }
    change(row, sources => sources.map(current => current.id === source.id ? { ...current, images: [...current.images, ...accepted], error, needsReview: current.needsReview || (accepted.length > 0 && current.evaluation !== "unreviewed") } : current));
  };
  const importDrafts = (row: number, incoming: SourceDraft[]) => change(row, sources => {
    const byId = new Map(incoming.map(source => [source.id, source]));
    for (const source of sources) byId.delete(source.id);
    return [...sources, ...byId.values()];
  });
  return { byRow, add, patch, remove, removeImage, attach, importDrafts, scope: storage?.scope, persistent: Boolean(storage), loading: autosave.loading, unavailable: autosave.unavailable, statusFor: autosave.statusFor };
}

export function sourceCountLabel(sources: SourceDraft[], suggested: boolean): string {
  return `${sources.length} nháp · ${suggested ? 1 : 0} gợi ý`;
}
