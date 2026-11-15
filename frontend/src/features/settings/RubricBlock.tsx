// todo 12.11：星數量表區塊（US-01；FR-RUB-01～03；SDD D-2(c)、D-3、D-4(b)）。精靈與設定頁共用。
// 流程：檢視目前版本 → 三題 → AI 草稿逐句改 → 確認即 POST /rubrics 入庫（不可撤）。
// AI 失敗（503）時以目前版本 5 句為底稿手動改寫；手動版本不帶 interview.draft，後端不寫 ai_feedback。

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { ApiError } from "../../api/client";
import { fetchActiveRubric, keys } from "../../api/queries";
import type { InterviewAnswers } from "../../api/types";
import { ErrorBanner } from "../../components/standin/ErrorBanner";
import { LEVEL_MAX, QUESTIONS } from "./options";
import { confirmRubric, interviewRubric } from "./requests";

type Mode = "view" | "ask" | "draft" | "manual";

interface Props {
  onConfirmed?: (version: number) => void;
  // 訪談或草稿進行中（離開會遺失）時為 true；外層據此在換頁前先詢問
  onEditingChange?: (editing: boolean) => void;
}

export function RubricBlock({ onConfirmed, onEditingChange }: Props) {
  const qc = useQueryClient();
  const rubric = useQuery({ queryKey: keys.activeRubric, queryFn: fetchActiveRubric });
  const [mode, setMode] = useState<Mode>("view");
  const [answers, setAnswers] = useState<Partial<InterviewAnswers>>({});
  const [draft, setDraft] = useState<string[]>([]);
  const [levels, setLevels] = useState<string[]>([]);

  useEffect(() => {
    onEditingChange?.(mode !== "view");
    return () => onEditingChange?.(false);
  }, [mode, onEditingChange]);

  const interview = useMutation({
    mutationFn: interviewRubric,
    onSuccess: (res) => { setDraft(res.draft); setLevels(res.draft); setMode("draft"); },
    onError: (err) => {
      if (err instanceof ApiError && err.status === 503 && rubric.data) { setLevels(rubric.data.levels); setMode("manual"); }
    },
  });

  const confirm = useMutation({
    mutationFn: () => confirmRubric(levels, answers as InterviewAnswers, mode === "draft" ? draft : null),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: keys.activeRubric });
      setMode("view");
      onConfirmed?.(res.version);
    },
  });

  if (!rubric.data) return <ErrorBanner error={rubric.error} />;
  const current = rubric.data;
  const next = current.version + 1;
  const complete = QUESTIONS.every((q) => answers[q.id]);
  const levelsOk = levels.length === 5 && levels.every((s) => s.trim() !== "");
  const interviewErr = interview.error instanceof ApiError && interview.error.status === 503 ? null : interview.error;

  if (mode === "view") {
    return (
      <div>
        {confirm.data && <p className="banner banner-ok" role="status">量表 v{confirm.data.version} 已確認。</p>}
        <p>目前使用 <b>v{current.version}</b>{current.source === "default" ? "（預設）" : "（訪談產生）"}</p>
        <ol className="levels">
          {current.levels.map((s, i) => <li key={i}><b>{i + 1} 星</b><span>{s}</span></li>)}
        </ol>
        <div className="actions">
          <button type="button" className="primary" onClick={() => { setAnswers({}); interview.reset(); confirm.reset(); setMode("ask"); }}>
            用三個問題訂我自己的量表
          </button>
          <span className="muted small">不訂也可以，會沿用目前版本。</span>
        </div>
      </div>
    );
  }

  if (mode === "ask") {
    return (
      <div>
        <p className="muted">回答三題，AI 會擬一份 5 句草稿，你可以逐句改。</p>
        {QUESTIONS.map((q) => (
          <fieldset key={q.id} className="field">
            <legend>{q.text}</legend>
            <div className="choices">
              {q.options.map((o) => (
                <label key={o} className="choice">
                  <input type="radio" name={q.id} checked={answers[q.id] === o} onChange={() => setAnswers((a) => ({ ...a, [q.id]: o }))} />
                  {o}
                </label>
              ))}
            </div>
          </fieldset>
        ))}
        <ErrorBanner error={interviewErr} />
        <div className="actions">
          <button type="button" className="primary" disabled={!complete || interview.isPending}
            onClick={() => interview.mutate(answers as InterviewAnswers)}>
            {interview.isPending ? "產生中…" : "產生草稿"}
          </button>
          <button type="button" onClick={() => setMode("view")}>取消</button>
        </div>
      </div>
    );
  }

  return (
    <div>
      {mode === "draft" ? (
        <p><span className="tag tag-warn">AI 草稿</span> 逐句確認或修改，按「確認成為 v{next}」才會生效。</p>
      ) : (
        <div className="banner banner-warn" role="alert">
          AI 暫時無法產生草稿。你可以直接沿用 v{current.version}，或以下方目前的 5 句為底稿自己改寫。
        </div>
      )}
      <ol className="levels">
        {levels.map((s, i) => (
          <li key={i}>
            <label htmlFor={`level-${i}`}><b>{i + 1} 星</b></label>
            <textarea id={`level-${i}`} rows={2} maxLength={LEVEL_MAX} value={s}
              onChange={(e) => setLevels((l) => l.map((x, j) => (j === i ? e.target.value : x)))} />
          </li>
        ))}
      </ol>
      {!levelsOk && <p className="hint">5 句都要填寫。</p>}
      <ErrorBanner error={confirm.error} />
      <div className="head">
        <span className="muted small">確認後就不能修改，之後要改會再產生新版本。</span>
        <span className="actions">
          <button type="button" onClick={() => setMode("view")}>{mode === "manual" ? `沿用 v${current.version}` : "放棄草稿"}</button>
          <button type="button" className="primary" disabled={!levelsOk || confirm.isPending} onClick={() => confirm.mutate()}>
            確認成為 v{next}
          </button>
        </span>
      </div>
    </div>
  );
}
