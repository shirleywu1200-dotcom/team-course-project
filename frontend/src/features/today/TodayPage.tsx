import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

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

// 只對伺服器 YYYY-MM-DD 做曆日加一；不讀本機時鐘，也不換算時區。
function nextCalendarDay(value: string) {
  const [year, month, day] = value.split("-").map(Number);
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  const nextDay = day < days[month - 1] ? day + 1 : 1;
  const nextMonth = nextDay === 1 ? (month === 12 ? 1 : month + 1) : month;
  const nextYear = month === 12 && nextDay === 1 ? year + 1 : year;
  return `${nextYear.toString().padStart(4, "0")}-${String(nextMonth).padStart(2, "0")}-${String(nextDay).padStart(2, "0")}`;
}

export function TodayPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const [savedFeedback] = useState(() => (location.state as { feedbackSaved?: FeedbackOut } | null)?.feedbackSaved);
  const [createdTaskId] = useState(() => (location.state as { createdTaskId?: number } | null)?.createdTaskId);
  const [completed, setCompleted] = useState<CompleteOut | null>(null);
  useEffect(() => {
    if (savedFeedback || createdTaskId) navigate(".", { replace: true, state: null });
  }, [navigate, savedFeedback, createdTaskId]);
  const today = useQuery({ queryKey: keys.today, queryFn: () => api<TodayOut>("/meta/today") });
  const dueBefore = today.data ? nextCalendarDay(today.data.today) : undefined;
  const tasks = useQuery({ queryKey: keys.taskList({ due_before: dueBefore }),
    queryFn: () => api<TaskListOut>(`/tasks?due_before=${dueBefore}`), enabled: Boolean(dueBefore) });
  const pending = useQuery({ queryKey: keys.feedbackPending(), queryFn: () => api<PendingFeedbackOut>("/feedback/pending") });

  return <main className="wide">
    <h1>今日</h1>
    {createdTaskId && <p className="banner banner-ok" role="status"><span>已建立任務 #{createdTaskId}。</span>{" "}
      <Link to={`/tasks/${createdTaskId}`}>查看任務</Link>
    </p>}
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
