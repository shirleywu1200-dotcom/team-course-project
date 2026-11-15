// todo 12.11：設定與量表的寫入請求（資料存取）。畫面元件只呼叫這裡，不直接組請求。

import { api } from "../../api/client";
import type { AppSettings, InterviewAnswers } from "../../api/types";
import { changedFields, WIZARD_KEYS } from "./options";

export const saveSettings = (patch: Partial<AppSettings>) => api<AppSettings>("/settings", { method: "PUT", body: patch });

// D-2：完成＝有改的欄位先 PUT，再 complete；略過＝丟掉已填、只送 complete {skipped:true}
export async function completeOnboarding(saved: AppSettings, draft: AppSettings, skipped: boolean): Promise<AppSettings> {
  const patch = changedFields(saved, draft, WIZARD_KEYS);
  if (!skipped && Object.keys(patch).length > 0) await saveSettings(patch);
  return api<AppSettings>("/settings/onboarding/complete", { body: { skipped } });
}

export const interviewRubric = (answers: InterviewAnswers) =>
  api<{ ai_status: "ok"; draft: string[] }>("/rubrics/interview", { body: answers });

// D-3：AI 草稿版本帶 draft（後端記 ai_feedback）；手動版本不帶
export const confirmRubric = (levels: string[], answers: InterviewAnswers, draft: string[] | null) =>
  api<{ id: number; version: number }>("/rubrics", {
    body: { levels: levels.map((s) => s.trim()), interview: { ...answers, ...(draft ? { draft } : {}) } },
  });
