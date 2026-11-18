import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";

import { api } from "../../api/client";
import { fetchHistory } from "../../api/history";
import { keys, normalizeEventFilters, type EventFilter } from "../../api/queryKeys";
import type { components } from "../../api/types.generated";
import { DatePicker } from "../../components/DatePicker";
import { ErrorBanner } from "../../components/ErrorBanner";
import { HistoryEventList } from "../../components/history/HistoryEventList";
import type { HistoryItem } from "../../components/history/HistoryEventRow";

type ProjectList = components["schemas"]["ProjectListOut"];
type ProjectDetail = components["schemas"]["ProjectDetailOut"];
type TaskList = components["schemas"]["TaskListOut"];

const kinds = ["due", "annotation", "status", "task", "feedback", "goal", "baseline", "project"] as const;
const filterFields = ["project_id", "kind", "task_id", "batch_id", "from", "to", "limit", "offset"] as const;

function ProjectHistoryContent({ fixedProjectId }: { fixedProjectId?: number }) {
  const navigate = useNavigate();
  const [search, setSearch] = useSearchParams();
  const normalized = normalizeEventFilters(search);
  const applied = fixedProjectId === undefined ? normalized : normalizeEventFilters({ ...normalized, project_id: String(fixedProjectId) });
  const [draft, setDraft] = useState<EventFilter>(applied);
  useEffect(() => setDraft(applied), [search, fixedProjectId]);

  const projects = useQuery({ queryKey: keys.projectList({ include_archived: true }),
    queryFn: () => api<ProjectList>("/projects?include_archived=true"), enabled: fixedProjectId === undefined });
  const project = useQuery({ queryKey: keys.project(fixedProjectId ?? 0),
    queryFn: () => api<ProjectDetail>(`/projects/${fixedProjectId}`), enabled: fixedProjectId !== undefined });
  const taskFilter = draft.project_id ? { project_id: draft.project_id } : {};
  const tasks = useQuery({ queryKey: keys.taskList(taskFilter),
    queryFn: () => api<TaskList>(`/tasks${draft.project_id ? `?project_id=${draft.project_id}` : ""}`) });
  const history = useQuery({ queryKey: keys.events(applied), queryFn: () => fetchHistory(applied),
    enabled: fixedProjectId === undefined || project.data !== undefined });
  useEffect(() => {
    if (!history.data || history.data.items.length > 0 || history.data.total === 0 ||
        (applied.offset ?? 0) < history.data.total) return;
    const limit = applied.limit ?? 100;
    const lastPage = Math.floor((history.data.total - 1) / limit) * limit;
    const params = new URLSearchParams(search);
    params.set("offset", String(lastPage));
    setSearch(params, { replace: true });
  }, [history.data, applied.offset, applied.limit, search, setSearch]);

  const change = (patch: Partial<EventFilter>) => setDraft(current => ({ ...current, ...patch }));
  const writeSearch = (next: EventFilter) => {
    const params = new URLSearchParams(search);
    for (const field of filterFields) params.delete(field);
    for (const [field, value] of Object.entries(normalizeEventFilters(next))) {
      if (field === "project_id" && fixedProjectId !== undefined) continue;
      if (field === "limit" && value === 100) continue;
      if (field === "offset" && value === 0) continue;
      params.set(field, String(value));
    }
    setSearch(params);
  };
  const apply = () => writeSearch({ ...draft, offset: 0 });
  const batchFilter = (item: HistoryItem) => change({ batch_id: item.batch_id ?? undefined });
  const title = fixedProjectId === undefined ? "歷程" : project.data ? `${project.data.name}歷程` : "專案歷程";

  return <main className="wide">
    <h1>{title}</h1>
    {project.isError && <ErrorBanner error={project.error} />}
    <section className="card" aria-label="歷程篩選">
      <h2>篩選</h2>
      {fixedProjectId === undefined && <div className="field"><label htmlFor="history-project">專案</label>
        <select id="history-project" value={draft.project_id ?? ""} onChange={event => change({ project_id: event.target.value || undefined, task_id: undefined })}>
          <option value="">全部專案</option><option value="none">單點任務</option>
          {projects.data?.items.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select></div>}
      {projects.isError && <ErrorBanner error={projects.error} />}
      <div className="field"><label htmlFor="history-kind">類型</label>
        <select id="history-kind" value={draft.kind ?? ""} onChange={event => change({ kind: event.target.value as EventFilter["kind"] || undefined })}>
          <option value="">全部類型</option>{kinds.map(kind => <option key={kind} value={kind}>{kind}</option>)}
        </select></div>
      <div className="field"><label htmlFor="history-task">任務</label>
        <select id="history-task" value={draft.task_id ?? ""} onChange={event => change({ task_id: event.target.value ? Number(event.target.value) : undefined })}>
          <option value="">全部任務</option>{tasks.data?.items.map(task => <option key={task.id} value={task.id}>{task.title}</option>)}
        </select></div>
      {tasks.isError && <ErrorBanner error={tasks.error} />}
      <div className="field"><label htmlFor="history-batch">批次編號</label>
        <input id="history-batch" type="number" min="1" value={draft.batch_id ?? ""} onChange={event => change({ batch_id: event.target.value ? Number(event.target.value) : undefined })} /></div>
      <DatePicker id="history-from" label="起日" value={draft.from ?? ""} onChange={value => change({ from: value || undefined })} />
      <DatePicker id="history-to" label="迄日" value={draft.to ?? ""} onChange={value => change({ to: value || undefined })} />
      <button type="button" className="primary" onClick={apply}>套用</button>
    </section>
    <section aria-label="歷程結果">
      {(project.isPending && fixedProjectId !== undefined || history.isPending && !project.isError) && <p role="status">載入歷程中…</p>}
      {history.error && <><ErrorBanner error={history.error} /><button type="button" onClick={() => void history.refetch()}>重試</button></>}
      {history.data && !history.error && <>
        {history.isFetching && <p role="status">更新歷程中…</p>}
        <p>符合 {history.data.total} 筆歷程</p>
        {history.data.items.length === 0 ? <p>沒有符合條件的歷程。</p> :
          <HistoryEventList items={history.data.items} onOpenTask={item => item.task_id !== null && navigate(`/tasks/${item.task_id}`)}
            onOpenProjectHistory={item => item.project_id !== null && navigate(`/projects/${item.project_id}/history`)}
            onBatchFilter={batchFilter} />}
        <div className="actions">
          <button type="button" disabled={(applied.offset ?? 0) === 0} onClick={() => writeSearch({ ...applied, offset: Math.max(0, (applied.offset ?? 0) - (applied.limit ?? 100)) })}>上一頁</button>
          <button type="button" disabled={(applied.offset ?? 0) + (applied.limit ?? 100) >= history.data.total}
            onClick={() => writeSearch({ ...applied, offset: (applied.offset ?? 0) + (applied.limit ?? 100) })}>下一頁</button>
        </div>
      </>}
    </section>
  </main>;
}

export function ProjectHistoryPage() {
  const { projectId } = useParams();
  const id = projectId === undefined ? undefined : Number(projectId);
  if (projectId !== undefined && (!/^\d+$/.test(projectId) || !Number.isSafeInteger(id) || (id ?? 0) <= 0)) {
    return <main><h1>專案歷程</h1><p role="alert">無效的專案編號。</p></main>;
  }
  return <ProjectHistoryContent fixedProjectId={id} />;
}
