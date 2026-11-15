// 12.8 貼上與解析（FR-INB-03～08、spec 6.1）。
// ≤ 30 行同步回結果；> 30 行回 job_id，每 pollMs 查一次，完成、失敗或超過 pollLimitMs 就停止。

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { api, newIdempotencyKey } from "../../api/client";
import { fetchIngestJob, keys } from "../../api/queries";
import type { AiStatus, IngestJob, IngestResult, IngestSummary } from "../../api/types";
import { ErrorBanner } from "../../components/standin/ErrorBanner";

export const POLL_MS = 2_000;
export const POLL_LIMIT_MS = 60_000;   // spec 6.1：超過 60 秒停止輪詢，工作持續

const finished = (job?: IngestJob) => job?.status === "succeeded" || job?.status === "failed";

function Summary({ result, aiStatus }: { result: IngestSummary; aiStatus: AiStatus }) {
  return (
    <div role="status">
      {aiStatus !== "ok" && (
        <p className="banner banner-warn">AI 解析失敗，這批訊息沒有產生候選，請手動建立任務。</p>
      )}
      <p className="muted">
        新增 {result.created} 張候選；略過 {result.skipped} 則；重複 {result.duplicates} 則。
      </p>
      {result.unparsed_lines.length > 0 && (
        <p className="hint">第 {result.unparsed_lines.join("、")} 行無法辨識，修正後可重新貼上。</p>
      )}
    </div>
  );
}

interface Props {
  pollMs: number;
  pollLimitMs: number;
}

export function PasteBox({ pollMs, pollLimitMs }: Props) {
  const qc = useQueryClient();
  const [text, setText] = useState("");
  const [jobId, setJobId] = useState<number | null>(null);
  const [timedOut, setTimedOut] = useState(false);

  const ingest = useMutation({
    mutationFn: () => api<IngestResult>("/ingest", { body: { text }, idempotencyKey: newIdempotencyKey() }),
    onSuccess: (r) => {
      setText("");
      setTimedOut(false);
      if (r.mode === "async") setJobId(r.job_id);
      else {
        setJobId(null);
        qc.invalidateQueries({ queryKey: ["candidates"] });
      }
    },
  });

  const job = useQuery({
    queryKey: keys.ingestJob(jobId ?? 0),
    queryFn: () => fetchIngestJob(jobId!),
    enabled: jobId !== null && !timedOut,
    refetchInterval: (q) => (finished(q.state.data) ? false : pollMs),
  });

  useEffect(() => {
    if (jobId === null) return;
    const t = setTimeout(() => setTimedOut(true), pollLimitMs);
    return () => clearTimeout(t);
  }, [jobId, pollLimitMs]);

  const jobDone = finished(job.data);
  useEffect(() => {
    if (jobDone) qc.invalidateQueries({ queryKey: ["candidates"] });
  }, [jobDone, qc]);

  const polling = jobId !== null && !jobDone && !timedOut;
  const sync = ingest.data?.mode === "sync" ? ingest.data : null;

  return (
    <section className="card" aria-label="貼上與解析">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (text.trim()) ingest.mutate();
        }}
      >
        <div className="field">
          <label htmlFor="inbox-paste">貼上群組對話</label>
          <textarea id="inbox-paste" rows={4} value={text} onChange={(e) => setText(e.target.value)} />
        </div>
        <div className="head">
          <span className="muted">只存必要摘錄，不存整段對話</span>
          <button type="submit" className="primary" disabled={!text.trim() || ingest.isPending || polling}>
            解析
          </button>
        </div>
      </form>
      <ErrorBanner error={ingest.error} />
      {sync && <Summary result={sync.result} aiStatus={sync.ai_status} />}
      {polling && <p className="muted" role="status">背景解析中…</p>}
      {jobId !== null && timedOut && !jobDone && <p className="muted" role="status">仍在處理，稍後回收件匣查看。</p>}
      {job.data?.status === "succeeded" && job.data.result && (
        <Summary result={job.data.result} aiStatus={job.data.result.ai_status} />
      )}
      {job.data?.status === "failed" && <p className="banner banner-warn">{job.data.error}</p>}
    </section>
  );
}
