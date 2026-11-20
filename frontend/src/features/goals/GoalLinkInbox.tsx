import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api, ApiError } from "../../api/client";
import { runMutationWithInvalidation } from "../../api/queryCache";
import { keys } from "../../api/queryKeys";
import type { components } from "../../api/types.generated";
import { ErrorBanner } from "../../components/ErrorBanner";

type Goal = components["schemas"]["GoalOut"];
type PendingLinkItem = components["schemas"]["PendingLinkItem"];
type PendingLinkOut = components["schemas"]["PendingLinkOut"];
type GoalLinkIn = components["schemas"]["GoalLinkIn"];
type TaskEventOut = components["schemas"]["TaskEventOut"];

function GoalLinkRow({ item, goals }: { item: PendingLinkItem; goals: Goal[] }) {
  const qc = useQueryClient();
  const [choice, setChoice] = useState("");
  const [unchanged, setUnchanged] = useState(false);
  const mutation = useMutation({ mutationFn: () => {
    const body = { task_id: item.task_id, goal_id: choice === "none" ? null : Number(choice),
      expected_version: item.version } satisfies GoalLinkIn;
    return runMutationWithInvalidation(qc, "POST /goal-links", () =>
      api<TaskEventOut>("/goal-links", { method: "POST", body }));
  }, onError: error => {
    if (error instanceof ApiError && error.code === "STALE_VERSION") {
      void qc.invalidateQueries({ queryKey: keys.goalLinksPending() });
    }
    if (error instanceof ApiError && error.code === "NO_CHANGE") setUnchanged(true);
  } });
  const noChange = mutation.error instanceof ApiError && mutation.error.code === "NO_CHANGE";
  return <li className="card">
    <p>{item.title} · 完成日：{item.done_date} · {item.scope === "private" ? "私人" : "工作"}</p>
    <div className="field"><label htmlFor={`goal-link-${item.task_id}`}>{item.title}的關聯目標</label>
      <select id={`goal-link-${item.task_id}`} value={choice} onChange={event => { setChoice(event.target.value); setUnchanged(false); }}>
        <option value="">請明選</option><option value="none">不關聯</option>
        {goals.filter(goal => !goal.archived_at).map(goal => <option key={goal.id} value={goal.id}>{goal.title}</option>)}
      </select></div>
    <button type="button" disabled={!choice || mutation.isPending} onClick={() => mutation.mutate()}>確認{item.title}關聯</button>
    {mutation.error && !noChange && <ErrorBanner error={mutation.error} />}
    {unchanged && noChange && <p role="status">目前關聯未變更。</p>}
  </li>;
}

export function GoalLinkInbox({ goals }: { goals: Goal[] | undefined }) {
  const pending = useQuery({ queryKey: keys.goalLinksPending(),
    queryFn: () => api<PendingLinkOut>("/goal-links/pending") });
  return <section className="card" aria-label="待關聯任務">
    <h2>待關聯任務</h2>
    {pending.error ? <><ErrorBanner error={pending.error} />
      <button type="button" onClick={() => { void pending.refetch(); }}>重試待關聯清單</button></>
      : !pending.data ? <p role="status">載入待關聯任務中…</p>
        : pending.data.items.length === 0 ? <p>沒有待關聯任務。</p>
          : <ul>{pending.data.items.map(item =>
            <GoalLinkRow key={`${item.task_id}-${item.version}`} item={item} goals={goals ?? []} />)}</ul>}
  </section>;
}
