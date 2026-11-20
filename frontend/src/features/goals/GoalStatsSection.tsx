import { useQuery } from "@tanstack/react-query";

import { api } from "../../api/client";
import { keys } from "../../api/queryKeys";
import type { components } from "../../api/types.generated";
import { ErrorBanner } from "../../components/ErrorBanner";

type GoalStatsOut = components["schemas"]["GoalStatsOut"];
const energyLabels = { high: "高", mid: "中", low: "低" };

export function GoalStatsSection({ goalId, goalTitle }: { goalId: number | null; goalTitle: string | null }) {
  const stats = useQuery({ queryKey: keys.goalStats(goalId ?? 0),
    queryFn: () => api<GoalStatsOut>(`/goals/${goalId}/stats`), enabled: goalId !== null });
  return <section className="card" aria-label="目標統計">
    <h2>目標統計{goalTitle ? `：${goalTitle}` : ""}</h2>
    {goalId === null ? <p>選擇目標後查看統計。</p>
      : stats.error ? <><ErrorBanner error={stats.error} />
        <button type="button" onClick={() => { void stats.refetch(); }}>重試統計</button></>
        : !stats.data ? <p role="status">載入目標統計中…</p>
          : <>
            <dl>
              {stats.data.progress !== null && <>
                <dt>進度</dt><dd>{stats.data.progress.text}</dd>
                <dt>進度比例</dt><dd>{stats.data.progress.pct == null ? "—" : `${stats.data.progress.pct}%`}</dd>
              </>}
              <dt>關聯事件數</dt><dd>{stats.data.linked}</dd>
              <dt>平均實際星數</dt><dd>{stats.data.avg_actual ?? "—"}</dd>
              <dt>平均預設星數</dt><dd>{stats.data.avg_expected ?? "—"}</dd>
              <dt>逾期件數</dt><dd>{stats.data.overdue_count}</dd>
              <dt>預期精力</dt><dd>{energyLabels[stats.data.energy_plan]}</dd>
            </dl>
            <div aria-label="實際精力分布">
              <p>高：{stats.data.energy.high}</p><p>中：{stats.data.energy.mid}</p><p>低：{stats.data.energy.low}</p>
            </div>
            {stats.data.judgement !== null && <p>{stats.data.judgement}</p>}
            <p>{stats.data.judgement_note}</p>
          </>}
  </section>;
}
