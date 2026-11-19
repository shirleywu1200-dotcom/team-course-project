import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api, ApiError } from "../../api/client";
import { fetchActiveRubric, fetchTask } from "../../api/queries";
import { keys } from "../../api/queryKeys";
import type { components } from "../../api/types.generated";
import { ErrorBanner } from "../../components/ErrorBanner";
import { CurrentFeedbackCard } from "./CurrentFeedbackCard";
import { FeedbackForm } from "./FeedbackForm";

type Task = components["schemas"]["TaskOut"];
type FeedbackOut = components["schemas"]["FeedbackOut"];
const starSourceLabels = {
  self: "自行設定", ai_accepted: "採用 AI 建議", ai_edited: "調整 AI 建議", import_default: "匯入預設",
};

function FeedbackTaskContext({ task }: { task: Task }) {
  return <section className="card" aria-label="事前預設脈絡">
    <h2>事前預設</h2>
    <p>事前預設星數：{task.expected_stars}</p>
    <p>星數來源：{starSourceLabels[task.star_source]}</p>
    <p>事前量表版本：{task.rubric_id ?? "未設定"}</p>
    <p className="muted">這是建立任務時的預設脈絡；完成回報使用開啟表單時的有效量表。</p>
  </section>;
}

function NewFeedbackPanel({ taskId }: { taskId: number }) {
  const rubric = useQuery({ queryKey: keys.activeRubric, queryFn: fetchActiveRubric });
  const [openedRubricId, setOpenedRubricId] = useState<number | null>(null);
  useEffect(() => {
    if (openedRubricId !== null || rubric.isFetching || !rubric.data) return;
    setOpenedRubricId(rubric.data.id);
  }, [openedRubricId, rubric.data, rubric.isFetching]);
  if (openedRubricId !== null) return <FeedbackForm taskId={taskId} rubricId={openedRubricId} />;
  if (rubric.error) return <ErrorBanner error={rubric.error} />;
  if (rubric.isSuccess && rubric.data === null) return <p role="alert">目前沒有可用的量表版本。</p>;
  return <p role="status">載入目前量表中…</p>;
}

function FeedbackContent({ taskId }: { taskId: number }) {
  const task = useQuery({ queryKey: keys.task(taskId), queryFn: () => fetchTask(taskId) });
  const feedback = useQuery({ queryKey: keys.feedback(taskId),
    queryFn: () => api<FeedbackOut>(`/tasks/${taskId}/feedback`), enabled: task.data?.status === "done" });

  if (task.error) return <main><h1>完成回報</h1><ErrorBanner error={task.error} /></main>;
  if (!task.data) return <main><h1>完成回報</h1><p role="status">載入任務中…</p></main>;
  return <main className="wide">
    <h1>完成回報</h1>
    <p>{task.data.title}</p>
    <FeedbackTaskContext task={task.data} />
    {task.data.status !== "done" ? <p>任務尚未完成，不能填寫完成回報。</p>
      : feedback.isPending ? <p role="status">載入目前回報中…</p>
      : feedback.data ? <CurrentFeedbackCard feedback={feedback.data} />
      : feedback.error instanceof ApiError && feedback.error.code === "NOT_FOUND"
        ? <NewFeedbackPanel taskId={taskId} />
        : <ErrorBanner error={feedback.error} />}
    <Link to="/today">返回今日</Link>
  </main>;
}

export function TaskFeedbackPage() {
  const { taskId: rawId } = useParams();
  const taskId = Number(rawId);
  if (!rawId || !/^\d+$/.test(rawId) || !Number.isSafeInteger(taskId) || taskId <= 0) {
    return <main><h1>完成回報</h1><p role="alert">無效的任務編號。</p></main>;
  }
  return <FeedbackContent taskId={taskId} />;
}
