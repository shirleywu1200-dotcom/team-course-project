// todo 12.2：預計完成日調整與註記流程（US-12、US-13；FR-DUE、FR-MRK）。
// 流程：選新日期 → 選原因 → 我的任務選註記或稍後註記 → 送出。
// FR-AI-06：原因與註記一律不預選；外部原因只顯示「建議不計入」的提示。
//
// 可嵌入介面（PR #1 審查 D2，Dev-C 選方案 X）：{ taskId, onDone, onClose }。
// - 任務一律從 keys.task(taskId) 讀取，與 12.3 詳情頁共用同一份快取，不另存快照。
// - 使用者填寫期間若任務版本改變，清空輸入並提示，不帶著舊輸入以新版本送出。

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { api, ApiError } from "../../api/client";
import { daysBetween, directionOf, formatDelta } from "../../api/dates";
import { fetchReasons, fetchTask, keys } from "../../api/queries";
import { OWNER_ME, type AdjustDueResult, type Task } from "../../api/types";
import { ErrorBanner } from "../../components/standin/ErrorBanner";
import { MarkChoice, markPayload, type MarkValue } from "../../components/standin/MarkChoice";
import { isExternal, ReasonSelect } from "../../components/standin/ReasonSelect";

const WARNING_TEXT: Record<string, string> = {
  BEFORE_START: "新日期早於開始日。",
  MARK_IGNORED: "這不是你的任務，註記已忽略。",
};

export const VERSION_CHANGED_TEXT = "資料已更新，請確認後再操作";

export interface AdjustDuePanelProps {
  taskId: number;
  onDone: (result: AdjustDueResult) => void;
  onClose: () => void;
}

export function AdjustDuePanel({ taskId, onDone, onClose }: AdjustDuePanelProps) {
  const task = useQuery({ queryKey: keys.task(taskId), queryFn: () => fetchTask(taskId) });
  if (task.error) return <ErrorBanner error={task.error} />;
  if (!task.data) return <p className="muted">載入中…</p>;
  return <AdjustDueForm task={task.data} onDone={onDone} onClose={onClose} />;
}

interface FormProps {
  task: Task;
  onDone: (result: AdjustDueResult) => void;
  onClose: () => void;
}

function AdjustDueForm({ task, onDone, onClose }: FormProps) {
  const qc = useQueryClient();
  const reasons = useQuery({ queryKey: keys.reasons, queryFn: fetchReasons });
  const [newDue, setNewDue] = useState("");
  const [reason, setReason] = useState("");
  const [note, setNote] = useState("");
  const [mark, setMark] = useState<MarkValue>(null);
  const [versionChanged, setVersionChanged] = useState(false);

  const mine = task.owner === OWNER_ME;
  const delta = newDue ? daysBetween(task.latest_due, newDue) : null;
  const direction = delta ? directionOf(delta) : null;
  const dueReasons = reasons.data?.due ?? [];
  const external = isExternal(dueReasons, direction, reason);
  const dirty = newDue !== "" || reason !== "" || note !== "" || mark !== null;

  function resetForm() {
    setNewDue("");
    setReason("");
    setNote("");
    setMark(null);
  }

  const mutation = useMutation({
    mutationFn: () =>
      api<AdjustDueResult>(`/tasks/${task.id}/adjust-due`, {
        body: {
          new_due: newDue,
          expected_version: task.version,
          reason,
          note: note || null,
          ...(mine ? markPayload(mark) : { mark: null, defer_mark: false }),
        },
      }),
    onSuccess: (r) => {
      resetForm();   // 先清空，自己送出造成的版本變化才不會被當成「別處更新」
      qc.setQueryData(keys.task(task.id), r.task);
      qc.invalidateQueries({ queryKey: ["tasks"] });
      onDone(r);
    },
    onError: (err) => {
      if (err instanceof ApiError && err.code === "STALE_VERSION") {
        qc.invalidateQueries({ queryKey: keys.task(task.id) });
      }
    },
  });

  // 填寫期間任務版本改變（別處修改，或 STALE_VERSION 後重新載入）：清空輸入、提示使用者重做
  const lastVersion = useRef(task.version);
  useEffect(() => {
    if (task.version === lastVersion.current) return;
    lastVersion.current = task.version;
    if (dirty) {
      resetForm();
      mutation.reset();
      setVersionChanged(true);
    }
  }, [task.version, dirty, mutation]);

  function edit<T>(setter: (v: T) => void) {
    return (v: T) => {
      setVersionChanged(false);
      setter(v);
    };
  }

  function changeDate(value: string) {
    edit(setNewDue)(value);
    const d = value ? daysBetween(task.latest_due, value) : 0;
    if (d === 0 || directionOf(d) !== direction) setReason("");
  }

  const done = task.status === "done";
  const ready = !done && delta !== null && delta !== 0 && reason !== "" && (!mine || mark !== null);

  return (
    <section className="card" aria-label="調整預計完成日">
      <h2>調整預計完成日</h2>
      <dl className="summary">
        <dt>任務</dt>
        <dd>{task.title}</dd>
        <dt>負責人</dt>
        <dd>{task.owner}</dd>
        <dt>原訂（固定）</dt>
        <dd>{task.orig_due}</dd>
        <dt>最新預計</dt>
        <dd>{task.latest_due}</dd>
      </dl>
      {versionChanged && (
        <p className="banner banner-warn" role="alert">
          {VERSION_CHANGED_TEXT}
        </p>
      )}
      {done ? (
        <p className="banner banner-warn">已完成的任務不能調整預計完成日。</p>
      ) : (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (ready) mutation.mutate();
          }}
        >
          <div className="field">
            <label htmlFor={`new-due-${task.id}`}>新的預計完成日</label>
            <input id={`new-due-${task.id}`} type="date" value={newDue} onChange={(e) => changeDate(e.target.value)} />
          </div>
          {delta !== null && (
            <p className="muted" data-testid="delta">
              {task.latest_due} → {newDue}：{formatDelta(delta)}；相對原訂 {formatDelta(daysBetween(task.orig_due, newDue))}
            </p>
          )}
          <ReasonSelect
            id={`reason-${task.id}`}
            reasons={dueReasons}
            direction={direction}
            value={reason}
            onChange={edit(setReason)}
          />
          <div className="field">
            <label htmlFor={`note-${task.id}`}>備註（選填）</label>
            <input id={`note-${task.id}`} value={note} onChange={(e) => edit(setNote)(e.target.value)} />
          </div>
          {mine && (
            <MarkChoice name={`mark-${task.id}`} value={mark} onChange={edit(setMark)} externalHint={external} />
          )}
          <ErrorBanner error={mutation.error} />
          <div className="actions">
            <button type="submit" className="primary" disabled={!ready || mutation.isPending}>
              確認調整
            </button>
            <button type="button" onClick={onClose}>
              關閉
            </button>
          </div>
        </form>
      )}
      {mutation.data && (
        <div className="banner banner-ok" role="status">
          已調整為 {mutation.data.task.latest_due}
          {mutation.data.needs_mark && "，註記留待稍後補上"}。
          {mutation.data.warnings.map((w) => (
            <span key={w}> {WARNING_TEXT[w] ?? w}</span>
          ))}
        </div>
      )}
    </section>
  );
}
