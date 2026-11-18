import { useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { api } from "../../api/client";
import { keys, queryRoots } from "../../api/queryKeys";
import { fetchSettings } from "../../api/queries";
import type { components } from "../../api/types.generated";
import { ConfirmationPanel } from "../../components/ConfirmationPanel";
import { ErrorBanner } from "../../components/ErrorBanner";

type SettingsOut = components["schemas"]["SettingsOut"];
type SettingsPatch = components["schemas"]["SettingsPatch"];
type ExportOut = components["schemas"]["ExportOut"];
type PurgeIn = components["schemas"]["PurgeIn"];
type PurgeOut = components["schemas"]["PurgeOut"];
type RetentionDays = NonNullable<SettingsPatch["retention_days"]>;

async function clearSourceCaches(qc: QueryClient) {
  await Promise.all([
    qc.cancelQueries({ queryKey: queryRoots.candidates }),
    qc.cancelQueries({ queryKey: ["events"] }),
  ]);
  qc.removeQueries({ queryKey: queryRoots.candidates });
  qc.removeQueries({ queryKey: ["events"] });
  await Promise.all([
    qc.refetchQueries({ queryKey: queryRoots.candidates, type: "active" }),
    qc.refetchQueries({ queryKey: ["events"], type: "active" }),
  ]);
}

function RetentionSection({ saved }: { saved: SettingsOut }) {
  const qc = useQueryClient();
  const [draft, setDraft] = useState(saved.retention_days as RetentionDays);
  const [confirming, setConfirming] = useState(false);
  const [acknowledged, setAcknowledged] = useState(false);
  useEffect(() => setDraft(saved.retention_days as RetentionDays), [saved.retention_days]);
  const save = useMutation({
    mutationFn: (days: RetentionDays) => api<SettingsOut>("/settings", {
      method: "PUT", body: { retention_days: days } satisfies SettingsPatch,
    }),
    onSuccess: async (settings, days) => {
      qc.setQueryData(keys.settings, settings);
      setDraft(settings.retention_days as RetentionDays);
      if (days < saved.retention_days) await clearSourceCaches(qc);
      setConfirming(false);
      setAcknowledged(false);
    },
  });
  const submit = () => {
    save.reset();
    if (draft < saved.retention_days) {
      setAcknowledged(false);
      setConfirming(true);
    } else save.mutate(draft);
  };
  return <section className="card" aria-label="保存期限設定">
    <h2>保存期限</h2>
    <p>來源原文由伺服器每日依保存期限清除。縮短期限可能立即清除到期原文，且無法復原。</p>
    <div className="field">
      <label htmlFor="retention-days">保存期限</label>
      <select id="retention-days" value={draft} disabled={save.isPending || confirming}
        onChange={(event) => { save.reset(); setDraft(Number(event.target.value) as RetentionDays); }}>
        {[30, 90, 180].map((days) => <option key={days} value={days}>{days} 天</option>)}
      </select>
    </div>
    <ErrorBanner error={save.error} />
    {save.isSuccess && <p role="status">已儲存保存期限。</p>}
    {!confirming && <button type="button" disabled={save.isPending} onClick={submit}>儲存保存期限</button>}
    {confirming && <ConfirmationPanel title="確認縮短保存期限" canConfirm={acknowledged && !save.isPending}
      onCancel={() => { setConfirming(false); setAcknowledged(false); }} onConfirm={() => save.mutate(draft)}>
      <p>縮短保存期限可能立即清除到期原文，且不可復原。</p>
      <label><input type="checkbox" checked={acknowledged}
        onChange={(event) => setAcknowledged(event.target.checked)} />我了解可能立即清除且不可復原</label>
    </ConfirmationPanel>}
  </section>;
}

function downloadExport(data: ExportOut) {
  if (typeof data.exported_at !== "string" || !/^\d{4}-\d{2}-\d{2}/.test(data.exported_at) ||
      typeof data.counts !== "object" || data.counts === null ||
      typeof data.tables !== "object" || data.tables === null) {
    throw new Error("匯出內容不完整");
  }
  const date = data.exported_at.slice(0, 10).replaceAll("-", "");
  const blob = new Blob([JSON.stringify(data)], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  try {
    const link = document.createElement("a");
    link.href = url;
    link.download = `資料匯出-${date}.json`;
    document.body.append(link);
    try { link.click(); } finally { link.remove(); }
  } finally {
    URL.revokeObjectURL(url);
  }
}

function ExportSection() {
  const exportData = useMutation({
    mutationFn: async () => {
      const data = await api<ExportOut>("/export", { method: "POST" });
      downloadExport(data);
    },
  });
  return <section className="card" aria-label="匯出資料">
    <h2>匯出資料</h2>
    <p>下載伺服器產生的 JSON 資料快照。</p>
    <ErrorBanner error={exportData.error} />
    {exportData.isSuccess && <p role="status">資料已準備下載。</p>}
    <button type="button" disabled={exportData.isPending} onClick={() => exportData.mutate()}>下載資料匯出</button>
  </section>;
}

function PurgeSection() {
  const qc = useQueryClient();
  const [confirming, setConfirming] = useState(false);
  const [acknowledged, setAcknowledged] = useState(false);
  const purge = useMutation({
    mutationFn: () => api<PurgeOut>("/sources/purge", { method: "POST", body: { confirm: true } satisfies PurgeIn }),
    onSuccess: async () => {
      await clearSourceCaches(qc);
      // 任務詳情內嵌歷程（含原文），存在 tasks 根底下
      void qc.invalidateQueries({ queryKey: queryRoots.tasks });
      setConfirming(false);
      setAcknowledged(false);
    },
  });
  return <section className="card" aria-label="刪除所有來源原文">
    <h2>刪除所有來源原文</h2>
    <p>來源原文與 AI 原始輸出會被清除；任務、候選與歷程仍保留。此操作無法還原。</p>
    <ErrorBanner error={purge.error} />
    {purge.isSuccess && <p role="status">已清除 {purge.data.purged} 筆來源原文。</p>}
    {!confirming && <button type="button" onClick={() => { purge.reset(); setAcknowledged(false); setConfirming(true); }}>刪除所有來源原文</button>}
    {confirming && <ConfirmationPanel title="確認刪除來源原文" canConfirm={acknowledged && !purge.isPending}
      onCancel={() => { setConfirming(false); setAcknowledged(false); }} onConfirm={() => purge.mutate()}>
      <label><input type="checkbox" checked={acknowledged} onChange={(event) => setAcknowledged(event.target.checked)} />我確認刪除所有來源原文</label>
    </ConfirmationPanel>}
  </section>;
}

export function DataControlPage() {
  const settings = useQuery({ queryKey: keys.settings, queryFn: fetchSettings });
  return <main className="wide">
    <h1>資料控制</h1>
    {settings.isPending && <section className="card" aria-label="保存期限設定"><h2>保存期限</h2><p role="status">載入保存期限中…</p></section>}
    {settings.isError && <section className="card" aria-label="保存期限設定"><h2>保存期限</h2><button type="button" onClick={() => settings.refetch()}>重試讀取</button></section>}
    <ErrorBanner error={settings.error} />
    {settings.data && <RetentionSection saved={settings.data} />}
    <ExportSection />
    <PurgeSection />
  </main>;
}
