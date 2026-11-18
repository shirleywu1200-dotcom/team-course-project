import type { ReactNode } from "react";

import { DatePicker } from "../../components/DatePicker";
import { AIFallback } from "../../components/ai/AIFallback";
import { mondayOf, weeklyDisplay } from "./weeklyState";
import "./weeklyView.css";

export function WeekSelector({ weekStart, onSelectWeek, disabled = false }: {
  weekStart: string;
  onSelectWeek: (weekStart: string) => void;
  disabled?: boolean;
}) {
  return <DatePicker id="weekly-week" label="選擇週次" value={weekStart} disabled={disabled}
    onChange={(day) => { if (day) onSelectWeek(mondayOf(day)); }} />;
}

export function WeeklyReportColumns({ ai, manual }: { ai: ReactNode; manual: ReactNode }) {
  return <div className="weekly-columns">
    <section className="card" aria-label="AI 初稿區">{ai}</section>
    <section className="card" aria-label="人工版區">{manual}</section>
  </div>;
}

export function WeeklyAISection({ validated, aiStatus, draft, fallback }: {
  validated: boolean;
  aiStatus: "ok" | "unavailable" | "invalid_output" | null;
  draft: string | null;
  fallback: ReactNode;
}) {
  const mode = weeklyDisplay(validated, aiStatus, draft);
  if (mode === "not-generated") return <><p>尚未產生 AI 初稿。</p>{fallback}</>;
  if (mode === "ai-fallback" && aiStatus !== null) {
    return <AIFallback aiStatus={aiStatus} fallback={fallback}>{null}</AIFallback>;
  }
  if (mode === "events") return <>
    {!validated && <p role="status">初稿未通過歷程核對，以下為依目前歷程列出的事件清單</p>}
    {fallback}
  </>;
  return <div className="weekly-draft" aria-label="AI 初稿">{draft}</div>;
}

export function ManualWeeklySection({ draft, onChange, onSave, saving, saveStatus }: {
  draft: string;
  onChange: (draft: string) => void;
  onSave: () => void;
  saving: boolean;
  saveStatus?: string;
}) {
  return <div>
    <label htmlFor="weekly-manual">人工版</label>
    <textarea id="weekly-manual" value={draft} disabled={saving} onChange={(event) => onChange(event.target.value)} />
    <div className="actions"><button type="button" disabled={saving} onClick={onSave}>{saving ? "儲存中…" : "儲存人工版"}</button></div>
    {saveStatus && <p role="status">{saveStatus}</p>}
  </div>;
}
