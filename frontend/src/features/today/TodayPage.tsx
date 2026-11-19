import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useLocation } from "react-router-dom";

import { api } from "../../api/client";
import { keys } from "../../api/queryKeys";
import type { components } from "../../api/types.generated";
import { ErrorBanner } from "../../components/ErrorBanner";
import { PendingFeedbackSection } from "./PendingFeedbackSection";
import { TodayTaskSection } from "./TodayTaskSection";

type TodayOut = components["schemas"]["TodayOut"];
type TaskListOut = components["schemas"]["TaskListOut"];
type PendingFeedbackOut = components["schemas"]["PendingFeedbackOut"];
type CompleteOut = components["schemas"]["CompleteOut"];
type FeedbackOut = components["schemas"]["FeedbackOut"];

export function TodayPage() {
  const location = useLocation();
  const savedFeedback = (location.state as { feedbackSaved?: FeedbackOut } | null)?.feedbackSaved;
  const [completed, setCompleted] = useState<CompleteOut | null>(null);
  const today = useQuery({ queryKey: keys.today, queryFn: () => api<TodayOut>("/meta/today") });
  const tasks = useQuery({ queryKey: keys.taskList({ due_before: today.data?.today }),
    queryFn: () => api<TaskListOut>(`/tasks?due_before=${today.data!.today}`), enabled: Boolean(today.data) });
  const pending = useQuery({ queryKey: keys.feedbackPending(), queryFn: () => api<PendingFeedbackOut>("/feedback/pending") });

  return <main className="wide">
    <h1>今日</h1>
    {savedFeedback && <p className="banner banner-ok" role="status">
      完成回報已儲存。伺服器計算逾期天數：{savedFeedback.overdue_days} 天
    </p>}
    {completed && <div className="card" role="status">
      <p>{completed.task.title}已完成。</p>
      {completed.feedback_required && <div className="actions">
        <Link to={`/tasks/${completed.task.id}/feedback`}>填寫完成回報</Link>
        <button type="button" onClick={() => setCompleted(null)}>稍後補</button>
      </div>}
    </div>}
    <section aria-label="可動任務">
      <h2>待處理任務</h2>
      {(today.isPending || (today.data && tasks.isPending)) && <p role="status">載入今日任務中…</p>}
      {(today.error || tasks.error) && <ErrorBanner error={today.error || tasks.error} />}
      {today.data && tasks.data && !tasks.error && <TodayTaskSection tasks={tasks.data.items}
        today={today.data.today} onComplete={setCompleted} />}
    </section>
    <section aria-label="待補完成回報"><h2>待補完成回報</h2>
      {pending.isPending && <p role="status">載入待補清單中…</p>}
      {pending.error && <ErrorBanner error={pending.error} />}
      {pending.data && !pending.error && <PendingFeedbackSection items={pending.data.items} />}
    </section>
  </main>;
}
