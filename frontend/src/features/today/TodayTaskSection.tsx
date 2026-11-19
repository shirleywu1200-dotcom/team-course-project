import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { api, ApiError } from "../../api/client";
import { runMutationWithInvalidation } from "../../api/queryCache";
import { queryRoots } from "../../api/queryKeys";
import type { components } from "../../api/types.generated";
import { DatePicker } from "../../components/DatePicker";
import { ErrorBanner } from "../../components/ErrorBanner";

type Task = components["schemas"]["TaskOut"];
type Complete = components["schemas"]["Complete"];
type CompleteOut = components["schemas"]["CompleteOut"];

function CompleteTaskAction({ task, onComplete }: { task: Task; onComplete: (result: CompleteOut) => void }) {
  const qc = useQueryClient();
  const [showDate, setShowDate] = useState(false);
  const [doneDate, setDoneDate] = useState("");
  const mutation = useMutation({
    mutationFn: () => runMutationWithInvalidation(qc, "POST /tasks/{task_id}/complete", () =>
      api<CompleteOut>(`/tasks/${task.id}/complete`, {
        body: { expected_version: task.version, ...(showDate ? { done_date: doneDate } : {}) } satisfies Complete,
      })),
    onSuccess: onComplete,
    onError: error => {
      if (error instanceof ApiError && error.code === "STALE_VERSION") {
        setDoneDate("");
        setShowDate(false);
        void qc.invalidateQueries({ queryKey: queryRoots.tasks });
      }
    },
  });
  return <div>
    <button type="button" onClick={() => setShowDate(value => !value)}>
      補記{task.title}完成日
    </button>
    {showDate && <DatePicker id={`done-date-${task.id}`} label="完成日" value={doneDate} onChange={setDoneDate} />}
    <button type="button" disabled={mutation.isPending || (showDate && !doneDate)}
      onClick={() => mutation.mutate()}>完成{task.title}</button>
    {mutation.error && <ErrorBanner error={mutation.error} />}
  </div>;
}

function TodayTaskRow({ task, onComplete }: { task: Task; onComplete: (result: CompleteOut) => void }) {
  return <li className="card">
    <Link to={`/tasks/${task.id}`}>{task.title}</Link>
    <p>預計完成日：{task.latest_due} · 狀態：{task.status} · 事前預設星數：{task.expected_stars}</p>
    <CompleteTaskAction task={task} onComplete={onComplete} />
  </li>;
}

export function TodayTaskSection({ tasks, today, onComplete }: {
  tasks: Task[]; today: string; onComplete: (result: CompleteOut) => void;
}) {
  const actionable = tasks.filter(task => task.status !== "done" && task.latest_due <= today);
  const overdue = actionable.filter(task => task.latest_due < today);
  const dueToday = actionable.filter(task => task.latest_due === today);
  return <>
    {actionable.length === 0 && <p>今日沒有待處理任務。</p>}
    <section aria-label="逾期任務"><h2>逾期</h2>
      {overdue.length === 0 ? <p>沒有逾期任務。</p> : <ul>{overdue.map(task =>
        <TodayTaskRow key={task.id} task={task} onComplete={onComplete} />)}</ul>}
    </section>
    <section aria-label="今日任務"><h2>今日</h2>
      {dueToday.length === 0 ? <p>今天沒有到期任務。</p> : <ul>{dueToday.map(task =>
        <TodayTaskRow key={task.id} task={task} onComplete={onComplete} />)}</ul>}
    </section>
  </>;
}
