import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type ReactNode } from "react";

import { api, ApiError } from "../../api/client";
import { keys } from "../../api/queryKeys";
import { ErrorBanner } from "../../components/ErrorBanner";
import { AIFallback } from "../../components/ai/AIFallback";
import { ManualWeeklySection, WeeklyReportColumns } from "../weekly-report/weeklyView";
import { GoalStatsSection } from "./GoalStatsSection";

// 暫代 spec 5.13 GoalReportOut；#111 的 OpenAPI 型別落地後改引用 types.generated.ts 並刪除此形狀。
type GoalReportOut = {
  id: number;
  goal_id: number;
  ai_status: "ok" | "unavailable" | "invalid_output" | null;
  excluded_private: number;
  draft: string | null;
  validated: boolean;
  manual_text: string | null;
  updated_at: string;
};

function GoalDraftView({ report, fallback }: { report: GoalReportOut | undefined; fallback: ReactNode }) {
  if (!report) return <p>尚未產生 AI 初稿。</p>;
  if (report.ai_status === null) return <><p>尚未產生 AI 初稿。</p>{fallback}</>;
  if (report.ai_status !== "ok") return <AIFallback aiStatus={report.ai_status} fallback={fallback}>{null}</AIFallback>;
  if (!report.validated || !report.draft) return <>
    <p role="status">初稿未通過統計核對，以下顯示目標統計。</p>{fallback}
  </>;
  return <div className="weekly-draft" aria-label="AI 初稿">{report.draft}</div>;
}

export function GoalReportArea({ goalId, goalTitle }: { goalId: number; goalTitle: string }) {
  const qc = useQueryClient();
  const reportKey = keys.goalReport(goalId);
  const [manualDraft, setManualDraft] = useState("");
  const [dirty, setDirty] = useState(false);
  const [saveStatus, setSaveStatus] = useState("");
  const reportQuery = useQuery({ queryKey: reportKey,
    queryFn: () => api<GoalReportOut>(`/goals/${goalId}/report`), retry: false });
  const report = reportQuery.data;
  const missing = reportQuery.error instanceof ApiError && reportQuery.error.status === 404
    && reportQuery.error.code === "NOT_FOUND";

  useEffect(() => {
    if (report && !dirty) setManualDraft(report.manual_text ?? "");
  }, [report, dirty]);

  const retainResponse = (response: GoalReportOut) => {
    // 產稿失敗的 200 退路仍顯示本次回應；不立即 GET 洗掉它。
    qc.setQueryData(reportKey, response);
  };
  const generate = useMutation({
    mutationFn: () => api<GoalReportOut>(`/goals/${goalId}/report/draft`, { method: "POST" }),
    onSuccess: retainResponse,
  });
  const save = useMutation({
    mutationFn: () => api<GoalReportOut>(`/goals/${goalId}/report/manual`,
      { method: "PUT", body: { manual_text: manualDraft } }),
    onSuccess: (response) => {
      retainResponse(response);
      setManualDraft(response.manual_text ?? "");
      setDirty(false);
      setSaveStatus("已儲存人工版");
    },
  });

  const statsFallback = <GoalStatsSection goalId={goalId} goalTitle={goalTitle} />;
  const ai = reportQuery.isFetching ? <p role="status">讀取最新目標回報中…</p>
    : <GoalDraftView report={report} fallback={statsFallback} />;

  return <section aria-label={`目標回報：${goalTitle}`}>
    <h2>目標回報：{goalTitle}</h2>
    {reportQuery.isPending ? <p role="status">載入目標回報中…</p>
      : reportQuery.error && !missing ? <><ErrorBanner error={reportQuery.error} />
        <button type="button" onClick={() => { void reportQuery.refetch(); }}>重試目標回報</button></>
        : <>
          {missing && <p>尚未產生回報</p>}
          <button type="button" disabled={generate.isPending || save.isPending}
            onClick={() => generate.mutate()}>{generate.isPending ? "產生中…" : report ? "重新產生初稿" : "產生初稿"}</button>
          {generate.error && <ErrorBanner error={generate.error} />}
          {save.error && <ErrorBanner error={save.error} message={save.error instanceof ApiError
            && save.error.code === "PAYLOAD_TOO_LARGE" ? "人工版超過 20,000 字，請縮短後再儲存。" : undefined} />}
          {report && !reportQuery.isFetching && report.excluded_private > 0
            && <p>已排除 {report.excluded_private} 件私人任務</p>}
          <WeeklyReportColumns ai={<><h3>AI 初稿</h3>{ai}</>} manual={<><h3>人工版</h3>
            <ManualWeeklySection draft={manualDraft} saving={save.isPending}
              onChange={value => { setManualDraft(value); setDirty(true); setSaveStatus(""); }}
              onSave={() => save.mutate()} saveStatus={saveStatus} /></>} />
        </>}
  </section>;
}
