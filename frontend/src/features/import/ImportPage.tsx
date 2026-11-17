// todo 12.7：匯入精靈（US-04；SDD docs/dev-b/12-7-sdd.md）。
// 版面 D-5：左欄目標＋原文，右欄對應＋診斷＋保存；≤ 760px 上下堆疊。
// 列與診斷只來自最近一次 preview 回應；本頁自管的只有 skip、confirmed 兩個狀態，輸入一改就清掉。

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";

import { ApiError, api, newIdempotencyKey } from "../../api/client";
import { queryRoots } from "../../api/queryKeys";
import type { ColumnIndexes, ImportCommitResult, ImportPreview } from "../../api/types";
import { ErrorBanner } from "../../components/ErrorBanner";
import { buildCommitBody, canCommit, type Target } from "./commit";
import { DiagnoseTable } from "./DiagnoseTable";
import { MappingPanel } from "./MappingPanel";
import { TargetPicker, type Dest } from "./TargetPicker";

function commitErrorMessage(err: unknown): string | null {
  if (!(err instanceof ApiError)) return null;
  if (err.code === "VALIDATION_ERROR" && Array.isArray(err.details.rows)) {
    const rows = (err.details.rows as number[]).map((i) => i + 1).join("、");
    return `第 ${rows} 列仍有錯誤，請修正原文後重新預覽。`;
  }
  if (err.code === "EMPTY_SELECTION") return "至少要有 1 列可匯入。";
  return null;
}

export function ImportPage() {
  const qc = useQueryClient();
  const [dest, setDest] = useState<Dest>({ mode: "new", newName: "", projectId: null });
  const [text, setText] = useState("");
  const [skip, setSkip] = useState<Set<number>>(new Set());
  const [confirmed, setConfirmed] = useState(false);
  const [aiRunId, setAiRunId] = useState<ImportPreview["column_map"]["ai_run_id"]>(null);
  const inputRevision = useRef(0);

  const target: Target | null = dest.mode === "new" ? "new" : dest.projectId;
  const ready = text.trim() !== "" && target !== null && (dest.mode === "existing" || dest.newName.trim() !== "");

  const preview = useMutation({
    onMutate: () => inputRevision.current,
    mutationFn: (columnMap?: ColumnIndexes) =>
      api<ImportPreview>("/projects/import/preview", {
        body: {
          text, target,
          ...(target === "new" ? { new_name: dest.newName.trim() } : {}),
          ...(columnMap ? { column_map: columnMap } : {}),
        },
      }),
    onSuccess: (response, _map, revision) => {
      // 原文／目標已變更時，不讓晚回的舊預覽帶回舊 AI 呼叫識別。
      if (revision !== inputRevision.current) return;
      if (response.column_map.ai_run_id != null) setAiRunId(current => current ?? response.column_map.ai_run_id);
      setSkip(new Set());
      setConfirmed(false);
    },
  });

  const commit = useMutation({
    mutationFn: (body: ReturnType<typeof buildCommitBody>) =>
      api<ImportCommitResult>("/projects/import/commit", { body, idempotencyKey: newIdempotencyKey() }),
    onSuccess: () => {
      inputRevision.current++;
      setAiRunId(null);
      preview.reset();
      setText("");
      qc.invalidateQueries({ queryKey: queryRoots.projects });
      qc.invalidateQueries({ queryKey: queryRoots.tasks });
    },
    onError: (err) => {
      if (!commitErrorMessage(err)) qc.invalidateQueries({ queryKey: queryRoots.projects });
    },
  });

  // 目標或原文一改，舊的預覽就不再對應目前輸入（D-1、D-4）
  const invalidate = () => {
    inputRevision.current++;
    setAiRunId(null);
    preview.reset();
    commit.reset();
    setSkip(new Set());
    setConfirmed(false);
  };

  const data = preview.data;
  const check = data ? canCommit(data, confirmed, skip) : null;
  const toggleSkip = (index: number) =>
    setSkip((s) => {
      const next = new Set(s);
      if (!next.delete(index)) next.add(index);
      return next;
    });
  const lines = text ? text.split("\n").length : 0;
  const commitMsg = commitErrorMessage(commit.error);

  return (
    <main className="wide">
      <h1>匯入專案</h1>
      <p className="muted">原訂日期以匯入的結束日為準；保存後要改原訂，需走基準更正。</p>
      <div className="import-split">
        <div className="import-left">
          <TargetPicker dest={dest} onChange={(d) => { setDest(d); invalidate(); }} />
          <section className="card" aria-label="貼上表格區">
            <form onSubmit={(e) => { e.preventDefault(); if (ready) preview.mutate(undefined); }}>
              <div className="field">
                <label htmlFor="import-text">貼上表格</label>
                <p className="muted">從試算表複製，含首列表頭；逗號或 Tab 分隔，最多 500 列。要補正錯誤列，直接改這裡再預覽。</p>
                <textarea id="import-text" rows={14} value={text}
                  onChange={(e) => { setText(e.target.value); invalidate(); }} />
              </div>
              <div className="head">
                <span className="muted">{lines} 行・{text.length} 字</span>
                <button type="submit" className="primary" disabled={!ready || preview.isPending}>預覽</button>
              </div>
            </form>
            <ErrorBanner error={preview.error} />
          </section>
        </div>

        <div>
          {commit.data && (
            <p className="banner banner-ok" role="status">
              已建立 {commit.data.created} 個任務、略過 {commit.data.skipped} 列（專案 #{commit.data.project_id}）。
            </p>
          )}
          {data && (
            <>
              <MappingPanel key={JSON.stringify(data.column_map)} preview={data} confirmed={confirmed}
                busy={preview.isPending} onConfirm={() => setConfirmed(true)} onApply={(m) => preview.mutate(m)} />
              {data.column_map.mapped_by !== null && (
                <DiagnoseTable preview={data} skip={skip} onToggleSkip={toggleSkip} />
              )}
              <section className="card head" aria-label="保存">
                {check?.ok ? (
                  <span>將建立 {data.rows.length - skip.size} 個任務、略過 {skip.size} 列，寫入一筆匯入基準。</span>
                ) : (
                  <span className="hint">{check?.reason}</span>
                )}
                <button type="button" className="primary" disabled={!check?.ok || commit.isPending}
                  onClick={() => target !== null && commit.mutate(buildCommitBody({ target, newName: dest.newName }, data.rows, skip,
                    { ...data.column_map, ai_run_id: aiRunId }))}>
                  保存基準
                </button>
              </section>
              {commitMsg ? <div className="banner banner-error" role="alert">{commitMsg}</div> : <ErrorBanner error={commit.error} />}
            </>
          )}
        </div>
      </div>
    </main>
  );
}
