import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../../api/client";
import { keys } from "../../api/queryKeys";
import type { components } from "../../api/types.generated";
import { ErrorBanner } from "../../components/ErrorBanner";
import { AdjustDuePanel } from "../due-adjust/AdjustDuePanel";
import { GanttChart } from "./gantt/GanttChart";
import { ProjectSummary } from "./ProjectSummary";
import { ProjectTaskTable } from "./ProjectTaskTable";
import "./project-overview.css";

type GanttOut = components["schemas"]["GanttOut"];
type ProjectDetail = components["schemas"]["ProjectDetailOut"];

function ProjectOverviewContent({ projectId }: { projectId: number }) {
  const qc = useQueryClient();
  const [selectedTaskId, setSelectedTaskId] = useState<number | null>(null);
  const project = useQuery({ queryKey: keys.project(projectId), queryFn: () => api<ProjectDetail>(`/projects/${projectId}`) });
  const gantt = useQuery({ queryKey: keys.gantt(projectId), queryFn: () => api<GanttOut>(`/projects/${projectId}/gantt`) });

  if (project.error || gantt.error) return <main><h1>專案現況</h1><ErrorBanner error={project.error || gantt.error} />
    <button type="button" onClick={() => { void project.refetch(); void gantt.refetch(); }}>重試</button></main>;
  if (!project.data || !gantt.data) return <main><h1>專案現況</h1><p role="status">載入專案現況中…</p></main>;

  return <main className="wide">
    <header><h1>{project.data.name}</h1>
      <p>範圍：{project.data.scope === "private" ? "私人" : "工作"}{project.data.archived_at && " · 已封存"}</p>
      <div className="actions"><Link to={`/projects/${projectId}/history`}>專案歷程</Link>
        <Link to={`/projects/${projectId}/bulk-shift`}>整批順延</Link></div>
    </header>
    {(project.isFetching || gantt.isFetching) && <p role="status">更新專案現況中…</p>}
    <ProjectSummary summary={gantt.data.summary} />
    <section className="card" aria-label="專案任務"><h2>任務</h2>
      <ProjectTaskTable rows={gantt.data.rows} onAdjust={setSelectedTaskId} /></section>
    {selectedTaskId !== null && <section className="card" aria-label="改預計日面板">
      <AdjustDuePanel taskId={selectedTaskId} onClose={() => setSelectedTaskId(null)} onDone={() => {
        setSelectedTaskId(null);
        void qc.invalidateQueries({ queryKey: keys.gantt(projectId) });
      }} />
    </section>}
    <section className="card" aria-label="甘特圖"><h2>甘特圖</h2>
      <div className="project-gantt-scroll"><GanttChart gantt={gantt.data} /></div>
    </section>
  </main>;
}

export function ProjectOverviewPage() {
  const { projectId: rawId } = useParams();
  const projectId = Number(rawId);
  if (!rawId || !/^\d+$/.test(rawId) || !Number.isSafeInteger(projectId) || projectId <= 0) {
    return <main><h1>專案現況</h1><p role="alert">無效的專案編號。</p></main>;
  }
  return <ProjectOverviewContent projectId={projectId} />;
}
