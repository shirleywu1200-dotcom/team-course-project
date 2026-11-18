import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";

import { fetchTask } from "../../api/queries";
import { keys, queryRoots } from "../../api/queryKeys";
import type { components } from "../../api/types.generated";
import { ErrorBanner } from "../../components/ErrorBanner";
import { BaselineCorrectionLink } from "../baseline/BaselineCorrection";
import { AdjustDuePanel } from "../due-adjust/AdjustDuePanel";
import { StartAdjustmentPanel } from "./StartAdjustmentPanel";
import { TaskHistorySection } from "./TaskHistorySection";

type Task = components["schemas"]["TaskOut"];

function TaskHeader({ task }: { task: Task }) {
  return <header><h1>{task.title}</h1><p>負責人：{task.owner} · {task.scope}</p>
    {task.project_id !== null && <Link to={`/projects/${task.project_id}`}>查看專案</Link>}
  </header>;
}

function TaskFacts({ task }: { task: Task }) {
  return <section aria-label="任務資訊" className="card">
    <h2>任務資訊</h2>
    <dl>
      <dt>狀態</dt><dd>{task.status}</dd>
      <dt>開始日</dt><dd>{task.start}</dd>
      <dt>原訂日</dt><dd>{task.orig_due}</dd>
      <dt>最新預計日</dt><dd>{task.latest_due}</dd>
      <dt>差距天數</dt><dd>{task.delta_days}</dd>
      <dt>完成條件</dt><dd>{task.done_when || "未設定"}</dd>
      <dt>提醒</dt><dd>{task.remind}</dd>
      <dt>預設星數</dt><dd>{task.expected_stars}</dd>
      <dt>星數來源</dt><dd>{task.star_source}</dd>
    </dl>
  </section>;
}

function BaselineInvalidationBoundary({ task, children }: { task: Task; children: ReactNode }) {
  const qc = useQueryClient();
  const previous = useRef(task.orig_due);
  useEffect(() => {
    if (previous.current === task.orig_due) return;
    previous.current = task.orig_due;
    void qc.invalidateQueries({ queryKey: queryRoots.events });
    void qc.invalidateQueries({ queryKey: queryRoots.gantt });
    void qc.invalidateQueries({ queryKey: queryRoots.projects });
  }, [task.orig_due, qc]);
  return <>{children}</>;
}

export function TaskDetailPage() {
  const { taskId: rawId } = useParams();
  const taskId = Number(rawId);
  const valid = Number.isSafeInteger(taskId) && taskId > 0;
  const qc = useQueryClient();
  const task = useQuery({ queryKey: keys.task(taskId), queryFn: () => fetchTask(taskId), enabled: valid });
  const [showDue, setShowDue] = useState(false);
  const [showStart, setShowStart] = useState(false);
  if (!valid) return <main><h1>任務不存在</h1></main>;
  if (task.error) return <main><h1>任務詳情</h1><ErrorBanner error={task.error} /></main>;
  if (!task.data) return <main><h1>任務詳情</h1><p role="status">載入任務中…</p></main>;
  return <main className="wide">
    <TaskHeader task={task.data} />
    <TaskFacts task={task.data} />
    <div className="actions">
      <button type="button" onClick={() => setShowStart(true)}>調整開始日</button>
      <button type="button" onClick={() => setShowDue(true)}>改預計日</button>
    </div>
    {showStart && <StartAdjustmentPanel task={task.data} onClose={() => setShowStart(false)} />}
    {showDue && <AdjustDuePanel taskId={taskId} onClose={() => setShowDue(false)} onDone={() => {
      setShowDue(false);
      void qc.invalidateQueries({ queryKey: queryRoots.events });
      void qc.invalidateQueries({ queryKey: queryRoots.gantt });
    }} />}
    <BaselineInvalidationBoundary task={task.data}><BaselineCorrectionLink task={task.data} /></BaselineInvalidationBoundary>
    <TaskHistorySection taskId={taskId} />
  </main>;
}
