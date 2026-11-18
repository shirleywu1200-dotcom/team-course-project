// 日期只作日曆運算；不換算伺服器時間戳或推算事件日期。
export function mondayOf(day: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(day);
  if (!match) throw new Error("日期須為 YYYY-MM-DD");
  const date = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])));
  if (date.toISOString().slice(0, 10) !== day) throw new Error("無效日期");
  const daysSinceMonday = (date.getUTCDay() + 6) % 7;
  date.setUTCDate(date.getUTCDate() - daysSinceMonday);
  return date.toISOString().slice(0, 10);
}

export function currentWeekStart(now = new Date()): string {
  const today = [now.getFullYear(), String(now.getMonth() + 1).padStart(2, "0"), String(now.getDate()).padStart(2, "0")].join("-");
  return mondayOf(today);
}

// 只根據本次回應的穩定欄位決定展示；不使用子元件掛載後才會變的狀態。
export function weeklyDisplay(validated: boolean, aiStatus: "ok" | "unavailable" | "invalid_output" | null, draft: string | null) {
  if (aiStatus === null) return "not-generated";
  if (aiStatus !== "ok") return "ai-fallback";
  if (!validated || !draft?.trim()) return "events";
  return "draft";
}
