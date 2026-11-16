// Dev-B 收件匣（12.8）、設定與量表（12.11）的 MSW 資料與預設 handlers；由 server.tsx 匯出，既有測試的匯入路徑不變。
import { http, HttpResponse } from "msw";

import type { AppSettings, Candidate, Rubric } from "../api/types";
import { API } from "./handlers";

export function makeCandidate(over: Partial<Candidate> = {}): Candidate {
  return {
    id: 21, kind: "delay", certainty: "sure", state: "open",
    task: { id: 2, title: "畫面規格 v1", latest_due: "2026-11-13", orig_due: "2026-11-13", version: 1 },
    proposed: { new_due: "2026-11-18" }, quote: "畫面規格 v1 確定延到 11/18", speaker: "阿德", spoken_at: "10:12",
    note: null, suggest: null, ...over,
  };
}

// 12.11 D-1(c)：預設回「已啟用」，既有頁面不會被守門導向精靈；守門另測。文字取自遷移 0003。
export function makeSettings(over: Partial<AppSettings> = {}): AppSettings {
  return {
    default_scope: "work", role: "project_owner", report_audience: "manager", confirm_time: "18:00",
    confirm_cap_min: 5, remind_default: "morning", retention_days: 30,
    energy_def_high: "需要長時間專注、做判斷或創作；做完需要休息才能接著做別的事。",
    energy_def_mid: "需要集中注意力，但被打斷後能接續；做完仍有餘力。",
    energy_def_low: "照流程或慣例即可完成，不太需要思考；可利用零碎時間做。",
    goal_types_enabled: ["growth", "time", "expectation"], onboarded_at: "2026-11-15T09:00:00+08:00", ...over,
  };
}

export const RUBRIC_V0: Rubric = {
  id: 1, version: 0, source: "default", interview: null, created_at: "2026-11-15T09:00:00+08:00",
  levels: [
    "未達成：完成條件大部分沒有達到，需要重做或補做。",
    "部分達成：完成條件只達到一部分，仍缺少重要項目。",
    "符合預設：完成條件達到，品質與事前預期一致。",
    "優於預設：完成條件達到，且品質或完整度優於事前預期。",
    "遠超預設：成果明顯超出原本範圍或預期，可作為範例。",
  ],
};

export const devbHandlers = [
  http.get(`${API}/settings`, () => HttpResponse.json(makeSettings())),
  http.get(`${API}/rubrics`, () => HttpResponse.json({ items: [RUBRIC_V0], total: 1 })),
  http.get(`${API}/candidates`, () => HttpResponse.json({ items: [], total: 0 })),
];
