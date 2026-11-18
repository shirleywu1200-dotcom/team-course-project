import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { api } from "../../api/client";
import { fetchHistory } from "../../api/history";
import { fetchReasons } from "../../api/queries";
import { keys, queryRoots } from "../../api/queryKeys";
import type { components } from "../../api/types.generated";
import { ErrorBanner } from "../../components/ErrorBanner";
import { HistoryEventList } from "../../components/history/HistoryEventList";
import type { HistoryItem } from "../../components/history/HistoryEventRow";
import { MarkChoice, type MarkValue } from "../../components/MarkChoice";
import { ReasonSelect } from "../../components/ReasonSelect";

type Annotation = components["schemas"]["Annotation"];
type AnnotationOut = components["schemas"]["AnnotationOut"];

function AnnotationPanel({ item, onClose }: { item: HistoryItem; onClose: () => void }) {
  const qc = useQueryClient();
  const reasons = useQuery({ queryKey: keys.reasons, queryFn: fetchReasons });
  const [mark, setMark] = useState<MarkValue>(null);
  const [reason, setReason] = useState("");
  const [note, setNote] = useState("");
  const direction = item.delta_days! > 0 ? "later" : "earlier";
  const mutation = useMutation({
    mutationFn: () => {
      if (mark === null || mark === "defer") throw new Error("請先選擇註記");
      return api<AnnotationOut>(`/events/${item.id}/annotations`, {
        body: { mark, reason: reason || null, note: note || null } satisfies Annotation,
      });
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryRoots.events });
      void qc.invalidateQueries({ queryKey: keys.task(item.task_id!) });
      void qc.invalidateQueries({ queryKey: queryRoots.timeManagement });
      onClose();
    },
  });
  return <section className="card" aria-label="註記面板">
    <h3>{item.effective_mark === null ? "補註記" : "改註記"}</h3>
    <MarkChoice name={`history-mark-${item.id}`} value={mark} onChange={value => {
      if (value === "defer") onClose();
      else setMark(value);
    }} />
    {reasons.error && <ErrorBanner error={reasons.error} />}
    <ReasonSelect id={`history-reason-${item.id}`} reasons={reasons.data?.due ?? []}
      direction={direction} value={reason} onChange={setReason} />
    <div className="field"><label htmlFor={`history-note-${item.id}`}>註記備註</label>
      <textarea id={`history-note-${item.id}`} value={note} onChange={event => setNote(event.target.value)} /></div>
    {mutation.error && <ErrorBanner error={mutation.error} />}
    <button type="button" disabled={mark === null || mutation.isPending} onClick={() => mutation.mutate()}>儲存註記</button>
    <button type="button" onClick={onClose}>取消</button>
  </section>;
}

export function TaskHistorySection({ taskId }: { taskId: number }) {
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<HistoryItem | null>(null);
  const filters = { task_id: taskId, limit: 100, offset };
  const history = useQuery({ queryKey: keys.events(filters), queryFn: () => fetchHistory(filters) });
  useEffect(() => {
    if (!history.data || offset < history.data.total || offset === 0) return;
    setOffset(Math.max(0, Math.floor((history.data.total - 1) / 100) * 100));
  }, [history.data, offset]);
  return <section aria-label="任務歷程">
    <h2>任務歷程</h2>
    {history.isPending && <p role="status">載入歷程中…</p>}
    {history.error && <><ErrorBanner error={history.error} /><button type="button" onClick={() => void history.refetch()}>重試歷程</button></>}
    {history.data && !history.error && <>
      {history.data.items.length === 0 ? <p>本任務目前沒有符合條件的歷程。</p>
        : <HistoryEventList items={history.data.items} onAnnotate={setSelected} />}
      <p>共 {history.data.total} 筆</p>
      <button type="button" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 100))}>上一頁</button>
      <button type="button" disabled={offset + 100 >= history.data.total} onClick={() => setOffset(offset + 100)}>下一頁</button>
    </>}
    {selected && <AnnotationPanel item={selected} onClose={() => setSelected(null)} />}
  </section>;
}
