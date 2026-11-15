// 12.8 單張候選卡片（SDD 第 3 節，依原型 V4 candCard）。
// 動作成功後把結果交給上層放進「已處理」；清單本身只從 candidates 查詢取得。
// STALE_VERSION、CANDIDATE_NOT_OPEN 只重新載入清單，讓使用者自己重按，不自動重送。

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api, ApiError, newIdempotencyKey } from "../../api/client";
import type { Candidate, DecideResult } from "../../api/types";
import { ErrorBanner } from "../../components/standin/ErrorBanner";

const KIND_LABEL: Record<Candidate["kind"], string> = {
  delay: "延期", done: "完成", stuck: "卡住", unclear: "待釐清", unmatched: "待配對",
};
const SUGGEST_LABEL = { delay: "我確認：延期", done: "我確認：完成", stuck: "我確認：卡住" };
const RELOAD_CODES = new Set(["STALE_VERSION", "CANDIDATE_NOT_OPEN"]);

interface Props {
  candidate: Candidate;
  onDecided: (r: DecideResult) => void;
}

export function CandidateCard({ candidate: c, onDecided }: Props) {
  const qc = useQueryClient();
  const initialDue = c.kind === "delay" ? c.proposed?.new_due : c.suggest?.kind === "delay" ? c.suggest.new_due : "";
  const [newDue, setNewDue] = useState(initialDue ?? "");
  const [title, setTitle] = useState(c.quote ?? "");
  const [due, setDue] = useState("");   // FR-INB-14：期限由你確認，不預填

  const mutation = useMutation({
    mutationFn: ({ action, body }: { action: string; body?: unknown }) =>
      api<DecideResult>(`/candidates/${c.id}/${action}`, { body: body ?? {}, idempotencyKey: newIdempotencyKey() }),
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ["candidates"] });
      qc.invalidateQueries({ queryKey: ["tasks"] });
      onDecided(r);
    },
    onError: (err) => {
      if (err instanceof ApiError && RELOAD_CODES.has(err.code)) qc.invalidateQueries({ queryKey: ["candidates"] });
    },
  });
  const busy = mutation.isPending;
  const version = c.task?.version;
  const dueBody = () => (newDue ? { new_due: newDue } : {});

  const confirm = () => mutation.mutate({ action: "confirm",
    body: { ...(c.kind === "delay" ? dueBody() : {}), expected_version: version } });
  const clarify = () => mutation.mutate({ action: "clarify",
    body: { ...(c.suggest?.kind === "delay" ? dueBody() : {}), expected_version: version } });
  const createTask = () => mutation.mutate({ action: "create-task", body: { title: title.trim(), owner: c.speaker, due } });
  const ignore = () => mutation.mutate({ action: "ignore" });

  const dateField = (
    <div className="field">
      <label htmlFor={`cand-due-${c.id}`}>新的預計完成日</label>
      <input id={`cand-due-${c.id}`} type="date" value={newDue} onChange={(e) => setNewDue(e.target.value)} />
    </div>
  );

  return (
    <article className="card">
      <div className="head">
        <span>
          <span className="tag tag-kind">{KIND_LABEL[c.kind]}</span> <b>{c.task?.title ?? "未對應任務"}</b>
        </span>
      </div>
      <blockquote className="quote">
        {c.quote === null ? <span className="muted">原句已刪除</span> : `「${c.quote}」`}
        <small>
          {c.speaker}
          {c.spoken_at && `・${c.spoken_at}`}・來源：貼上
        </small>
      </blockquote>

      {c.kind === "delay" && c.task && (
        <>
          <p>最新預計 {c.task.latest_due} →</p>
          {dateField}
          <p className="muted">原訂 {c.task.orig_due} 不會被覆寫</p>
        </>
      )}
      {c.kind === "done" && <p>狀態 → 完成</p>}
      {c.kind === "stuck" && <p>狀態 → 卡住</p>}
      {c.kind === "unclear" && (
        <>
          {c.note && <p className="hint">{c.note}</p>}
          {c.suggest?.kind === "delay" && dateField}
        </>
      )}
      {c.kind === "unmatched" && (
        <>
          {c.note && <p className="hint">{c.note}</p>}
          <div className="field">
            <label htmlFor={`cand-title-${c.id}`}>標題</label>
            <input id={`cand-title-${c.id}`} value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <p className="muted">負責人：{c.speaker}</p>
          <div className="field">
            <label htmlFor={`cand-new-${c.id}`}>期限</label>
            <input id={`cand-new-${c.id}`} type="date" value={due} onChange={(e) => setDue(e.target.value)} />
          </div>
        </>
      )}

      <ErrorBanner error={mutation.error} />
      <div className="actions">
        {(c.kind === "delay" || c.kind === "done" || c.kind === "stuck") && (
          <button type="button" className="primary" disabled={busy || !c.task || (c.kind === "delay" && !newDue)}
                  onClick={confirm}>
            確認
          </button>
        )}
        {c.kind === "unclear" && c.suggest && c.task && (
          <button type="button" disabled={busy || (c.suggest.kind === "delay" && !newDue)} onClick={clarify}>
            {SUGGEST_LABEL[c.suggest.kind]}
          </button>
        )}
        {c.kind === "unmatched" && (
          <button type="button" className="primary" disabled={busy || !title.trim() || !due} onClick={createTask}>
            建立新任務
          </button>
        )}
        {/* 待釐清以「忽略」為主要按鈕，避免誤採用 AI 建議（原型 V4） */}
        <button type="button" className={c.kind === "unclear" ? "primary" : undefined} disabled={busy} onClick={ignore}>
          忽略
        </button>
      </div>
    </article>
  );
}
