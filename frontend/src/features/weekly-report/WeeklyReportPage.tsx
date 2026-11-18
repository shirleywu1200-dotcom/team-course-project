import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { ApiError } from "../../api/client";
import { keys, queryRoots } from "../../api/queryKeys";
import { ErrorBanner } from "../../components/ErrorBanner";
import { WeeklyEventFallback } from "./WeeklyEventFallback";
import { currentWeekStart, mondayOf, weeklyDisplay } from "./weeklyState";
import { fetchWeeklyByWeek, generateWeeklyDraft, saveWeeklyManual, type WeeklyReport } from "./weeklyRequests";
import { ManualWeeklySection, WeekSelector, WeeklyAISection, WeeklyReportColumns } from "./weeklyView";

function selectedWeek(raw: string | null) {
  try { return raw ? mondayOf(raw) : currentWeekStart(); }
  catch { return currentWeekStart(); }
}

function WeeklyReportContent({ weekStart, onSelectWeek }: { weekStart: string; onSelectWeek: (week: string, dirty: boolean) => void }) {
  const qc = useQueryClient();
  const [urlParams, setUrlParams] = useSearchParams();
  const [manualDraft, setManualDraft] = useState("");
  const [dirty, setDirty] = useState(false);
  const [saveStatus, setSaveStatus] = useState("");
  const reportQuery = useQuery({
    queryKey: keys.weeklyReportByWeek(weekStart),
    queryFn: () => fetchWeeklyByWeek(weekStart),
    retry: false,
  });
  const report = reportQuery.data;
  const missing = reportQuery.error instanceof ApiError && reportQuery.error.status === 404;

  useEffect(() => {
    if (!report || report.week_start !== weekStart || urlParams.get("report_id") === String(report.id)) return;
    const next = new URLSearchParams(urlParams);
    next.set("report_id", String(report.id));
    setUrlParams(next, { replace: true });
  }, [report, weekStart, urlParams, setUrlParams]);

  useEffect(() => {
    if (report && !dirty) setManualDraft(report.manual_text ?? "");
  }, [report, dirty]);

  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    const guardLink = (event: MouseEvent) => {
      const target = event.target;
      const link = target instanceof Element ? target.closest("a[href]") : null;
      if (!link || link.getAttribute("href")?.startsWith("#")) return;
      if (window.confirm("人工版有未儲存的修改，要捨棄並離開週報嗎？")) return;
      event.preventDefault();
      event.stopImmediatePropagation();
    };
    window.addEventListener("beforeunload", warn);
    document.addEventListener("click", guardLink, true);
    return () => {
      window.removeEventListener("beforeunload", warn);
      document.removeEventListener("click", guardLink, true);
    };
  }, [dirty]);

  const retainResponse = (response: WeeklyReport) => {
    // H2：保留本次 POST 的降級回應；其他週報鍵只標 stale，不立刻 GET 洗掉提示。
    void qc.invalidateQueries({ queryKey: queryRoots.weeklyReports, refetchType: "none" });
    qc.setQueryData(keys.weeklyReportByWeek(response.week_start), response);
    qc.setQueryData(keys.weeklyReport(response.id), response);
  };

  const generate = useMutation({
    mutationFn: () => generateWeeklyDraft({ week_start: weekStart }),
    onSuccess: retainResponse,
  });
  const save = useMutation({
    mutationFn: () => saveWeeklyManual(report!.id, { manual_text: manualDraft }),
    onSuccess: (response) => {
      retainResponse(response);
      setDirty(false);
      setSaveStatus("已儲存人工版");
    },
  });

  // 同週重讀時暫不展示舊 AI；人工編輯草稿仍留在本地。
  const showReport = !missing ? report : undefined;
  const showAI = showReport && !reportQuery.isFetching && !reportQuery.error ? showReport : undefined;
  const fallback = showAI ? <WeeklyEventFallback items={showAI.items} /> : null;
  return <main className="wide">
    <h1>週報</h1>
    <WeekSelector weekStart={weekStart} onSelectWeek={(week) => onSelectWeek(week, dirty)} disabled={save.isPending} />
    {reportQuery.isFetching && <p role="status">讀取週報中…</p>}
    {missing && <p>本週尚未產生週報</p>}
    {reportQuery.error && !missing && <><ErrorBanner error={reportQuery.error} /><button type="button" onClick={() => void reportQuery.refetch()}>重試讀取</button></>}
    {(missing || showReport) && <button type="button" disabled={generate.isPending || save.isPending}
      onClick={() => generate.mutate()}>{generate.isPending ? "產生中…（最長約 60 秒）" : report ? "重新產生初稿" : "產生初稿"}</button>}
    {generate.error && <ErrorBanner error={generate.error} />}
    {save.error && <ErrorBanner error={save.error} message={save.error instanceof ApiError && save.error.code === "PAYLOAD_TOO_LARGE"
      ? "人工版超過 20,000 字，請縮短後再儲存。" : undefined} />}
    {showReport && <>
      {!reportQuery.isFetching && !reportQuery.error && <p>產生當下排除 {showReport.excluded_private} 項私人任務。</p>}
      <WeeklyReportColumns
        ai={<><h2>AI 初稿</h2>{showAI ? <><WeeklyAISection validated={showAI.validated} aiStatus={showAI.ai_status}
          draft={showAI.draft} fallback={fallback} />{weeklyDisplay(showAI.validated, showAI.ai_status, showAI.draft) === "draft" && fallback}</> : <p>讀取最新週報中…</p>}</>}
        manual={<><h2>人工版</h2><ManualWeeklySection draft={manualDraft} saving={save.isPending}
          onChange={(value) => { setManualDraft(value); setDirty(true); setSaveStatus(""); }}
          onSave={() => save.mutate()} saveStatus={saveStatus} /></>}
      />
    </>}
  </main>;
}

export function WeeklyReportPage() {
  const [params, setParams] = useSearchParams();
  const weekStart = selectedWeek(params.get("week_start"));
  useEffect(() => {
    if (params.get("week_start") === weekStart) return;
    const next = new URLSearchParams(params);
    next.set("week_start", weekStart);
    next.delete("report_id");
    setParams(next, { replace: true });
  }, [params, setParams, weekStart]);
  const onSelectWeek = (week: string, dirty: boolean) => {
    if (week === weekStart) return;
    if (dirty && !window.confirm("人工版有未儲存的修改，要捨棄並切換週次嗎？")) return;
    setParams({ week_start: week });
  };
  return <WeeklyReportContent key={weekStart} weekStart={weekStart} onSelectWeek={onSelectWeek} />;
}
