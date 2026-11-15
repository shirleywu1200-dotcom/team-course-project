// todo 12.11：設定選項、分組與量表訪談題目的單一來源（SDD docs/dev-b/12-11-sdd.md D-4、D-5）。
// 選項值對照 backend/app/api/routes_settings.py SettingsPatch；精靈與設定頁都從這裡讀。

import type { AppSettings, GoalType, SettingsKey } from "../../api/types";

export type Option<T> = readonly [value: T, label: string];

export const OPTIONS = {
  role: [["project_owner", "專案負責人"], ["wbs_owner", "負責一個 WBS"], ["both", "兩者都有"]],
  default_scope: [["work", "工作"], ["private", "私人（不會送 AI）"]],
  report_audience: [["manager", "主管"], ["client", "客戶"], ["none", "不需要週報"]],
  confirm_time: [["12:00", "12:00"], ["18:00", "18:00"], ["21:00", "21:00"]],
  confirm_cap_min: [[3, "3 分鐘"], [5, "5 分鐘"], [10, "10 分鐘"]],
  remind_default: [["morning", "當天早上"], ["eve_before", "前一晚"], ["none", "不提醒"]],
  retention_days: [[30, "30 天"], [90, "90 天"], [180, "180 天"]],
} as const satisfies { [K in SettingsKey]?: readonly Option<AppSettings[K]>[] };

export type RadioKey = keyof typeof OPTIONS;

export const GOALS: readonly (readonly [GoalType, string, string])[] = [
  ["growth", "能力成長", "完成事件數"],
  ["time", "時間配置", "每週確認分鐘數"],
  ["expectation", "績效期待", "對應專案完成比"],
];

export type GroupId = "role" | "inbox" | "rubric" | "goal" | "rhythm" | "retention";

// keys：該組會寫進 PUT /settings 的欄位；收件來源與量表不寫設定（量表走 POST /rubrics）
export const GROUPS: readonly { id: GroupId; name: string; keys: readonly SettingsKey[] }[] = [
  { id: "role", name: "角色與範圍", keys: ["role", "default_scope", "report_audience"] },
  { id: "inbox", name: "收件來源", keys: [] },
  { id: "rubric", name: "星數量表", keys: [] },
  { id: "goal", name: "目標與精力", keys: ["goal_types_enabled", "energy_def_high", "energy_def_mid", "energy_def_low"] },
  { id: "rhythm", name: "確認節奏", keys: ["confirm_time", "confirm_cap_min", "remind_default"] },
  { id: "retention", name: "原文保存", keys: ["retention_days"] },
];

export const groupOf = (id: GroupId) => GROUPS.find((g) => g.id === id)!;

// FR-SET-01 精靈 6 步：歡迎（null）＋ 5 組；原文保存只在設定頁（SDD D-5 前提）
export const WIZARD_STEPS: readonly (GroupId | null)[] = [null, "role", "inbox", "rubric", "goal", "rhythm"];
export const stepName = (id: GroupId | null) => (id ? groupOf(id).name : "歡迎");
export const WIZARD_KEYS: readonly SettingsKey[] = WIZARD_STEPS.flatMap((id) => (id ? groupOf(id).keys : []));

// FR-RUB-02 三個選擇題。選項文字為 Dev-B 草擬，待產品負責人確認（SDD 待釐清 6）
export const QUESTIONS = [
  { id: "q1", text: "什麼程度算「符合預設」（3 星）？", options: ["交付完成且品質達標", "按時交付即可", "對方確認收下即可"] },
  { id: "q2", text: "什麼情況給 5 顆星？", options: ["超出範圍或品質明顯突出", "提前完成且品質達標", "成果被拿去當範例"] },
  { id: "q3", text: "不同類型的任務要用不同標準嗎？", options: ["否，同一套標準", "是，依類型分開（本版只記錄，仍共用一套）"] },
] as const;

export const LEVEL_MAX = 200;

// 只取 keys 中與已存值不同的欄位，作為 PUT /settings 的部分更新本文
export function changedFields(saved: AppSettings, draft: AppSettings, keys: readonly SettingsKey[]): Partial<AppSettings> {
  const patch: Partial<AppSettings> = {};
  for (const k of keys) {
    if (JSON.stringify(saved[k]) !== JSON.stringify(draft[k])) Object.assign(patch, { [k]: draft[k] });
  }
  return patch;
}
