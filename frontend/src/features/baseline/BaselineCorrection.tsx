// todo 12.5：基準更正（US-08；FR-BAS）。
// 入口是任務詳情裡的小連結，不放在主要操作區（FR-BAS-01）。
// 兩段式：預覽影響並取得憑證 → 勾選聲明後才確認。原因與類型預設不選。

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api, ApiError } from "../../api/client";
import { fetchReasons, keys } from "../../api/queries";
import type { BaselinePreview, EventRow, Task } from "../../api/types";
import { ErrorBanner } from "../../components/standin/ErrorBanner";

const ACK_TEXT = "我確認這次更正不是為了讓延期看起來比較小";

export function BaselineCorrectionLink({ task }: { task: Task }) {
  const [open, setOpen] = useState(false);
  if (task.status === "done") return null;
  return (
    <div>
      {!open && (
        <button type="button" className="link-button" onClick={() => setOpen(true)}>
          原訂日期寫錯了？更正基準
        </button>
      )}
      {open && <BaselineCorrectionDialog task={task} onClose={() => setOpen(false)} />}
    </div>
  );
}

function BaselineCorrectionDialog({ task, onClose }: { task: Task; onClose: () => void }) {
  const qc = useQueryClient();
  const meta = useQuery({ queryKey: keys.reasons, queryFn: fetchReasons });
  const [newOrig, setNewOrig] = useState("");
  const [type, setType] = useState("");
  const [reason, setReason] = useState("");
  const [ack, setAck] = useState(false);

  const preview = useMutation({
    mutationFn: () =>
      api<BaselinePreview>(`/tasks/${task.id}/baseline-correction/preview`, {
        body: { new_orig_due: newOrig, type, reason, expected_version: task.version },
      }),
    onMutate: () => setAck(false),
    onError: (err) => {
      if (err instanceof ApiError && err.code === "STALE_VERSION") {
        qc.invalidateQueries({ queryKey: keys.task(task.id) });
      }
    },
  });

  const commit = useMutation({
    mutationFn: () =>
      api<{ task: Task; event: EventRow }>(`/tasks/${task.id}/baseline-correction/commit`, {
        body: { confirmation_token: preview.data!.confirmation_token, ack },
      }),
    onSuccess: (r) => {
      qc.setQueryData(keys.task(task.id), r.task);
      qc.invalidateQueries({ queryKey: ["tasks"] });
    },
    onError: (err) => {
      if (err instanceof ApiError && err.code === "CONFIRMATION_INVALID") {
        preview.reset();
        qc.invalidateQueries({ queryKey: keys.task(task.id) });
      }
    },
  });

  const canPreview = newOrig !== "" && type !== "" && reason !== "";
  const impact = preview.data?.impact;

  if (commit.data) {
    return (
      <section className="card" role="dialog" aria-label="基準更正">
        <p className="banner banner-ok" role="status">
          原訂日已更正為 {commit.data.task.orig_due}，舊值 {commit.data.event.from_value} 已留在歷程。
        </p>
        <button type="button" onClick={onClose}>
          關閉
        </button>
      </section>
    );
  }

  return (
    <section className="card" role="dialog" aria-label="基準更正">
      <h2>更正基準（原訂日）</h2>
      <p className="muted">
        只有原訂日期確實寫錯，或客戶、主管正式改變承諾日時才使用。舊的原訂日會永久留在歷程。
      </p>
      <div className="field">
        <label htmlFor="baseline-new">新的原訂日</label>
        <input
          id="baseline-new"
          type="date"
          value={newOrig}
          onChange={(e) => {
            setNewOrig(e.target.value);
            preview.reset();
          }}
        />
      </div>
      <fieldset className="field">
        <legend>類型</legend>
        <div className="choices">
          {(meta.data?.baseline_types ?? []).map((t) => (
            <label key={t.code} className="choice">
              <input
                type="radio"
                name="baseline-type"
                value={t.code}
                checked={type === t.code}
                onChange={() => {
                  setType(t.code);
                  preview.reset();
                }}
              />
              {t.label}
            </label>
          ))}
        </div>
      </fieldset>
      <div className="field">
        <label htmlFor="baseline-reason">原因</label>
        <select
          id="baseline-reason"
          value={reason}
          onChange={(e) => {
            setReason(e.target.value);
            preview.reset();
          }}
        >
          <option value="">請選擇原因</option>
          {(meta.data?.baseline_reasons ?? []).map((r) => (
            <option key={r.code} value={r.code}>
              {r.label}
            </option>
          ))}
        </select>
      </div>
      <ErrorBanner error={preview.error ?? commit.error} />
      {!impact && (
        <div className="actions">
          <button type="button" className="primary" disabled={!canPreview || preview.isPending} onClick={() => preview.mutate()}>
            預覽影響
          </button>
          <button type="button" onClick={onClose}>
            取消
          </button>
        </div>
      )}
      {impact && (
        <div aria-label="更正影響">
          <h2>更正後的影響</h2>
          <dl className="summary">
            <dt>原訂日</dt>
            <dd>
              {impact.orig_due.from} → {impact.orig_due.to}
            </dd>
            <dt>與基準差距</dt>
            <dd>
              {impact.gap_days.from} 天 → {impact.gap_days.to} 天
            </dd>
            <dt>已延期任務數</dt>
            <dd>
              {impact.project_delayed_count.from} → {impact.project_delayed_count.to}
            </dd>
            <dt>過去的日期調整</dt>
            <dd>{impact.past_due_events_kept} 筆，保留原樣，不重算</dd>
          </dl>
          <p className="muted">舊的原訂日 {impact.orig_due.from} 會永久留在歷程。</p>
          <label className="choice">
            <input type="checkbox" checked={ack} onChange={(e) => setAck(e.target.checked)} />
            {ACK_TEXT}
          </label>
          <div className="actions">
            <button type="button" className="primary" disabled={!ack || commit.isPending} onClick={() => commit.mutate()}>
              確認更正
            </button>
            <button type="button" onClick={onClose}>
              取消
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
