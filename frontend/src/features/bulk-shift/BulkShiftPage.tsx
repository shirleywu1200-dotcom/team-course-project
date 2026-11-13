// todo 12.4：整批順延（US-06；FR-BLK）。
// 流程：勾選任務 → 天數、原因 → 預覽（不寫入）→ 我的任務選統一註記 → 確認（單一交易）。
// 預設全選未完成任務；不自動推論相依。原因與註記預設不選（FR-AI-06）。

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { api, ApiError, newIdempotencyKey } from "../../api/client";
import { directionOf } from "../../api/dates";
import { fetchProjectTasks, fetchReasons, keys } from "../../api/queries";
import type { BulkCommitResult, BulkPreview, Task } from "../../api/types";
import { ErrorBanner } from "../../components/standin/ErrorBanner";
import { MarkChoice, markPayload, type MarkValue } from "../../components/standin/MarkChoice";
import { isExternal, ReasonSelect } from "../../components/standin/ReasonSelect";

const WARNING_TEXT: Record<string, string> = { BEFORE_TODAY: "早於今天", BEFORE_START: "早於開始日" };

export function BulkShiftPage() {
  const projectId = Number(useParams().projectId);
  return <BulkShift projectId={projectId} />;
}

export function BulkShift({ projectId }: { projectId: number }) {
  const qc = useQueryClient();
  const tasks = useQuery({ queryKey: keys.projectTasks(projectId), queryFn: () => fetchProjectTasks(projectId) });
  const reasons = useQuery({ queryKey: keys.reasons, queryFn: fetchReasons });
  const openTasks = useMemo(() => (tasks.data ?? []).filter((t) => t.status !== "done"), [tasks.data]);
  const doneCount = (tasks.data?.length ?? 0) - openTasks.length;

  const [selected, setSelected] = useState<Set<number> | null>(null);
  const [days, setDays] = useState("");
  const [reason, setReason] = useState("");
  const [note, setNote] = useState("");
  const [mark, setMark] = useState<MarkValue>(null);
  const [preview, setPreview] = useState<{ data: BulkPreview; key: string } | null>(null);

  useEffect(() => {
    if (selected === null && tasks.data) setSelected(new Set(openTasks.map((t) => t.id)));
  }, [selected, tasks.data, openTasks]);

  const dayNum = Number(days);
  const validDays = days !== "" && Number.isInteger(dayNum) && dayNum !== 0 && Math.abs(dayNum) <= 365;
  const direction = validDays ? directionOf(dayNum) : null;
  const dueReasons = reasons.data?.due ?? [];
  const chosen: Task[] = openTasks.filter((t) => selected?.has(t.id));
  const items = chosen.map((t) => ({ task_id: t.id, expected_version: t.version }));

  function invalidate() {
    setPreview(null);
    setMark(null);
  }

  const previewMut = useMutation({
    mutationFn: () =>
      api<BulkPreview>(`/projects/${projectId}/bulk-shift/preview`, { body: { items, days: dayNum, reason } }),
    onSuccess: (data) => setPreview({ data, key: newIdempotencyKey() }),
  });

  const commitMut = useMutation({
    mutationFn: () =>
      api<BulkCommitResult>(`/projects/${projectId}/bulk-shift/commit`, {
        idempotencyKey: preview!.key,
        body: {
          items,
          days: dayNum,
          reason,
          note: note || null,
          ...(preview!.data.mark_required ? markPayload(mark) : { mark: null, defer_mark: false }),
        },
      }),
    onSuccess: () => {
      invalidate();
      setSelected(null);
      qc.invalidateQueries({ queryKey: ["tasks"] });
    },
    onError: (err) => {
      if (err instanceof ApiError && err.code === "STALE_VERSION") {
        invalidate();
        setSelected(null);
        qc.invalidateQueries({ queryKey: keys.projectTasks(projectId) });
      }
    },
  });

  function toggle(id: number) {
    const next = new Set(selected ?? []);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelected(next);
    invalidate();
  }

  const canPreview = items.length > 0 && validDays && reason !== "";
  const canCommit = preview !== null && (!preview.data.mark_required || mark !== null) && !commitMut.isPending;

  return (
    <main>
      <h1>整批順延</h1>
      <section className="card" aria-label="選擇任務">
        <h2>選擇要順延的任務</h2>
        {doneCount > 0 && <p className="muted">已完成的 {doneCount} 項不列入。</p>}
        <table>
          <thead>
            <tr>
              <th>順延</th>
              <th>任務</th>
              <th>負責人</th>
              <th>最新預計</th>
            </tr>
          </thead>
          <tbody>
            {openTasks.map((t) => (
              <tr key={t.id}>
                <td>
                  <input
                    type="checkbox"
                    aria-label={`選擇 ${t.title}`}
                    checked={selected?.has(t.id) ?? false}
                    onChange={() => toggle(t.id)}
                  />
                </td>
                <td>{t.title}</td>
                <td>{t.owner}</td>
                <td>{t.latest_due}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="field">
          <label htmlFor="bulk-days">天數（負數為提前）</label>
          <input
            id="bulk-days"
            type="number"
            value={days}
            onChange={(e) => {
              setDays(e.target.value);
              const n = Number(e.target.value);
              if (!n || directionOf(n) !== direction) setReason("");
              invalidate();
            }}
          />
        </div>
        <ReasonSelect
          id="bulk-reason"
          reasons={dueReasons}
          direction={direction}
          value={reason}
          onChange={(v) => {
            setReason(v);
            invalidate();
          }}
        />
        <div className="field">
          <label htmlFor="bulk-note">備註（選填）</label>
          <input id="bulk-note" value={note} onChange={(e) => setNote(e.target.value)} />
        </div>
        <div className="actions">
          <button type="button" disabled={!canPreview || previewMut.isPending} onClick={() => previewMut.mutate()}>
            預覽
          </button>
        </div>
      </section>

      <ErrorBanner error={previewMut.error ?? commitMut.error} />
      {commitMut.data && (
        <p className="banner banner-ok" role="status">
          已順延 {commitMut.data.updated} 項（批次 #{commitMut.data.batch_id}）。
        </p>
      )}

      {preview && (
        <section className="card" aria-label="順延預覽">
          <h2>預覽（尚未寫入）</h2>
          <table>
            <thead>
              <tr>
                <th>任務</th>
                <th>負責人</th>
                <th>原日期</th>
                <th>新日期</th>
                <th>注意</th>
              </tr>
            </thead>
            <tbody>
              {preview.data.items.map((r) => (
                <tr key={r.task_id}>
                  <td>{r.title}</td>
                  <td>{r.owner}</td>
                  <td>{r.from}</td>
                  <td>{r.to}</td>
                  <td>{r.warnings.map((w) => WARNING_TEXT[w] ?? w).join("、")}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {preview.data.mark_required && (
            <>
              <p className="muted">
                其中 {preview.data.mine_count} 項是你的任務，會套用同一個註記；要逐項不同，之後在歷程補註記。
              </p>
              <MarkChoice
                name="bulk-mark"
                value={mark}
                onChange={setMark}
                externalHint={isExternal(dueReasons, direction, reason)}
              />
            </>
          )}
          <div className="actions">
            <button type="button" className="primary" disabled={!canCommit} onClick={() => commitMut.mutate()}>
              確認順延
            </button>
          </div>
        </section>
      )}
    </main>
  );
}
