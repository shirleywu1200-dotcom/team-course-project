// 12.8「已處理」的一筆：顯示決定結果；我的任務延期後在這裡補註記（FR-INB-10、FR-MRK）。
// 候選確認後就離開 open 清單，所以註記放在這裡，不放在候選卡片上。
// FR-AI-06：三選一與原因都不預選；「稍後註記」不呼叫 API。

import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api, newIdempotencyKey } from "../../api/client";
import { directionOf } from "../../api/dates";
import { fetchReasons, keys } from "../../api/queries";
import type { DecideResult } from "../../api/types";
import { ErrorBanner } from "../../components/standin/ErrorBanner";
import { MarkChoice, type MarkValue } from "../../components/standin/MarkChoice";
import { isExternal, ReasonSelect } from "../../components/standin/ReasonSelect";

function decision(r: DecideResult): string {
  const c = r.candidate;
  if (c.state === "ignored") return "忽略";
  if (c.kind === "unmatched") return "建立新任務";
  const kind = c.kind === "unclear" ? c.suggest?.kind : c.kind;
  if (kind === "delay") return r.task ? `延到 ${r.task.latest_due}` : "延期";
  return kind === "done" ? "完成" : "卡住";
}

function MarkForm({ eventId, delta }: { eventId: number; delta: number }) {
  const reasons = useQuery({ queryKey: keys.reasons, queryFn: fetchReasons });
  const [mark, setMark] = useState<MarkValue>(null);
  const [reason, setReason] = useState("");
  const [deferred, setDeferred] = useState(false);
  const direction = directionOf(delta);
  const dueReasons = reasons.data?.due ?? [];
  const mutation = useMutation({
    mutationFn: () =>
      api(`/events/${eventId}/annotations`, {
        body: { mark, reason: reason || null, note: null },
        idempotencyKey: newIdempotencyKey(),
      }),
  });

  if (deferred) return <p className="muted">註記留待稍後補上</p>;
  if (mutation.isSuccess) return <p className="muted">已註記</p>;
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (mark === "defer") setDeferred(true);
        else if (mark) mutation.mutate();
      }}
    >
      <ReasonSelect id={`ann-reason-${eventId}`} reasons={dueReasons} direction={direction} value={reason}
                    onChange={setReason} />
      <MarkChoice name={`ann-mark-${eventId}`} value={mark} onChange={setMark}
                  externalHint={isExternal(dueReasons, direction, reason)} />
      <ErrorBanner error={mutation.error} />
      <div className="actions">
        <button type="submit" className="primary" disabled={mark === null || mutation.isPending}>
          送出註記
        </button>
      </div>
    </form>
  );
}

export function DecidedItem({ result: r }: { result: DecideResult }) {
  const c = r.candidate;
  const ignored = c.state === "ignored";
  return (
    <div className="card done-item">
      <div className="head">
        <span>
          {c.task?.title ?? r.task?.title ?? "新任務"}・{decision(r)}
        </span>
        <span className="tag">{ignored ? "已忽略" : "已確認"}</span>
      </div>
      {c.quote && <p className="muted">「{c.quote}」</p>}
      {r.feedback_required && <p className="hint">完成回報可到今日頁補填</p>}
      {r.needs_mark && r.event && <MarkForm eventId={r.event.id} delta={r.event.delta_days ?? 0} />}
    </div>
  );
}
