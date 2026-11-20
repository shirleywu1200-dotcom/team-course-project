// 12.12 階段 1：所有目標頁測試共用此處的範例資料；形狀直接受生成型別檢查。
import type { components } from "../api/types.generated";
import { makeSerializedEvent, makeTask } from "./fixtures";

type Goal = components["schemas"]["GoalOut"];

const growth = {
  id: 1, type: "growth", title: "練習規格分析", period: "2026Q4", definition: "完成練習任務",
  target: 3, energy_plan: "high", project_id: null,
  created_at: "2026-11-19T09:00:00+08:00", archived_at: null,
} satisfies Goal;
const time = { ...growth, id: 2, type: "time", title: "安排確認時間", target: 60, energy_plan: "mid" } satisfies Goal;
const expectation = { ...growth, id: 3, type: "expectation", title: "完成專案", target: 0,
  energy_plan: "low", project_id: 1 } satisfies Goal;
const archived = { ...growth, id: 4, title: "已封存練習", archived_at: "2026-11-18T09:00:00+08:00" } satisfies Goal;
const linkResult = { task: makeTask({ id: 101, status: "done", goal_id: 1, version: 5 }),
  event: makeSerializedEvent({ task_id: 101, kind: "goal", field: "goal_id", to_value: "1" }) } satisfies components["schemas"]["TaskEventOut"];

export const goalFixtures = {
  growth, time, expectation, archived,
  list: { items: [growth, time, expectation, archived] } satisfies components["schemas"]["GoalListOut"],
  emptyList: { items: [] } satisfies components["schemas"]["GoalListOut"],
  projects: { items: [{ id: 1, name: "範例專案", scope: "work", audience: "none", line_group_id: null,
    created_at: "2026-11-01T09:00:00+08:00", updated_at: "2026-11-02T09:00:00+08:00", archived_at: null }],
    total: 1 } satisfies components["schemas"]["ProjectListOut"],
  insufficient: { progress: { text: "3 ／ 3 件完成事件", pct: 100 }, linked: 3,
    avg_actual: 4, avg_expected: 3.3, overdue_count: 1, energy: { high: 2, mid: 1, low: 0 },
    energy_plan: "high", min_sample: 5, judgement: null,
    judgement_note: "樣本 3 筆，不到 5 筆，只顯示不下結論" } satisfies components["schemas"]["GoalStatsOut"],
  timeStats: { progress: null, linked: 5, avg_actual: 4, avg_expected: 3,
    overdue_count: 2, energy: { high: 1, mid: 4, low: 0 }, energy_plan: "mid", min_sample: 5,
    judgement: "一致", judgement_note: "主要精力為中，與預期相同" } satisfies components["schemas"]["GoalStatsOut"],
  expectationStats: { progress: { text: "1 ／ 2 件專案任務完成", pct: 50 }, linked: 5,
    avg_actual: 3.4, avg_expected: 3, overdue_count: 2, energy: { high: 3, mid: 0, low: 2 },
    energy_plan: "low", min_sample: 5, judgement: "建議檢視",
    judgement_note: "主要精力為高，預期為低" } satisfies components["schemas"]["GoalStatsOut"],
  tiedStats: { progress: { text: "5 ／ 5 件完成事件", pct: 100 }, linked: 5,
    avg_actual: 4, avg_expected: 3, overdue_count: 0, energy: { high: 2, mid: 2, low: 1 },
    energy_plan: "high", min_sample: 5, judgement: "建議檢視",
    judgement_note: "主要精力並列：高、中" } satisfies components["schemas"]["GoalStatsOut"],
  zeroStats: { progress: { text: "0 ／ 0 件完成事件", pct: null }, linked: 0,
    avg_actual: null, avg_expected: null, overdue_count: 0, energy: { high: 0, mid: 0, low: 0 },
    energy_plan: "high", min_sample: 5, judgement: null,
    judgement_note: "樣本 0 筆，不到 5 筆，只顯示不下結論" } satisfies components["schemas"]["GoalStatsOut"],
  matrix: { items: [{ goal_id: 1, title: "練習規格分析", energy_plan: "high",
    energy: { high: 2, mid: 1, low: 0 }, linked: 3 }] } satisfies components["schemas"]["GoalMatrixOut"],
  emptyMatrix: { items: [] } satisfies components["schemas"]["GoalMatrixOut"],
  pending: { items: [{ task_id: 101, title: "範例已完成任務", project_id: 1, scope: "work",
    done_date: "2026-11-19", version: 4 }], total: 1 } satisfies components["schemas"]["PendingLinkOut"],
  emptyPending: { items: [], total: 0 } satisfies components["schemas"]["PendingLinkOut"],
  linkResult,
};
