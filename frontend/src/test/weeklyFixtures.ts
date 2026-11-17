// Phase 10 #23@cad3d46 的完整甲型範例；只引用 OpenAPI 生成型別，勿作產品型別。
import type { components } from "../api/types.generated";

type WeeklyReport = components["schemas"]["WeeklyReportOut"];
type WeeklyItem = components["schemas"]["WeeklyItemOut"];
const doneItem = {
  section: "done", task_id: 101, event_id: 201, title: "完成範例任務", owner: "我",
  done_date: "2026-11-10", orig_due: null, latest_due: null, blocked: null,
  event: { id: 201, ts: "2026-11-10T09:00:00+08:00", from_value: "doing", to_value: "done", delta_days: null },
} satisfies WeeklyItem;

const delayItem = {
  section: "delay", task_id: 102, event_id: 202, title: "調整範例任務", owner: "我",
  done_date: null, orig_due: "2026-11-12", latest_due: "2026-11-18", blocked: null,
  event: { id: 202, ts: "2026-11-11T10:00:00+08:00", from_value: "2026-11-12", to_value: "2026-11-16", delta_days: 4 },
} satisfies WeeklyItem;

const nextItem = {
  section: "next", task_id: 103, event_id: null, title: "下週範例任務", owner: "我",
  done_date: null, orig_due: null, latest_due: "2026-11-19", blocked: true, event: null,
} satisfies WeeklyItem;

export const weeklyReady = {
  id: 7, week_start: "2026-11-09", ai_status: "ok", excluded_private: 2,
  draft: "本週完成：範例任務。", items: [doneItem, delayItem, nextItem],
  validated: true, manual_text: "範例人工版：由使用者修改。", updated_at: "2026-11-16T10:00:00+08:00",
} satisfies WeeklyReport;

export const weeklyReconciliationFailed = {
  ...weeklyReady, draft: null, validated: false, items: [delayItem],
} satisfies WeeklyReport;

export const weeklyUnavailable = { ...weeklyReconciliationFailed, ai_status: "unavailable" } satisfies WeeklyReport;
export const weeklyInvalidOutput = { ...weeklyReconciliationFailed, ai_status: "invalid_output" } satisfies WeeklyReport;
export const weeklyRegenerated = {
  ...weeklyReady, draft: "重新產生的範例初稿。", updated_at: "2026-11-16T11:00:00+08:00",
} satisfies WeeklyReport;
export const weeklyEmpty = { ...weeklyReady, items: [], draft: "本週沒有可列的工作項目。" } satisfies WeeklyReport;

// 週次 GET 404 由 handler 回狀態碼，不建立假的 id=0 週報物件。
