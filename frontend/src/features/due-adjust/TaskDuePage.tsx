// 暫代頁面：承載 12.2 調整面板與 12.5 基準更正入口。
// 正式的任務詳情頁是 Dev-C 的 12.3，完成後把這兩個元件放進去，這個頁面即可移除。

import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { fetchTask, keys } from "../../api/queries";
import { ErrorBanner } from "../../components/standin/ErrorBanner";
import { BaselineCorrectionLink } from "../baseline/BaselineCorrection";
import { AdjustDuePanel } from "./AdjustDuePanel";

export function TaskDuePage() {
  const id = Number(useParams().taskId);
  const task = useQuery({ queryKey: keys.task(id), queryFn: () => fetchTask(id) });
  if (task.error) return <ErrorBanner error={task.error} />;
  if (!task.data) return <p className="muted">載入中…</p>;
  return (
    <main>
      <h1>{task.data.title}</h1>
      <AdjustDuePanel task={task.data} />
      <BaselineCorrectionLink task={task.data} />
    </main>
  );
}
