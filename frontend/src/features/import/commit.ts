// 12.7 保存條件與 commit 內容（SDD 第 2 節）。純函式，單獨測試。
// 前端條件只是避免白送；後端 commit 仍會每列重新驗證（AC-31）。

import type { ImportPreview, ImportRow } from "../../api/types";

export type Target = "new" | number;

export type CommitCheck = { ok: true } | { ok: false; reason: string };

export function canCommit(preview: ImportPreview, confirmed: boolean, skip: Set<number>): CommitCheck {
  const { mapped_by } = preview.column_map;
  if (mapped_by === null) return { ok: false, reason: "請先指定任務名稱與結束欄位" };
  if (mapped_by === "ai" && !confirmed) return { ok: false, reason: "請先確認欄位對應" };
  const unhandled = preview.rows.filter((r) => r.blocking && !skip.has(r.index)).length;
  if (unhandled > 0) return { ok: false, reason: `還有 ${unhandled} 列錯誤未處理` };
  if (!preview.rows.some((r) => !skip.has(r.index))) return { ok: false, reason: "至少要有 1 列可匯入" };
  return { ok: true };
}

export function buildCommitBody(dest: { target: Target; newName: string }, rows: ImportRow[], skip: Set<number>) {
  return {
    target: dest.target,
    ...(dest.target === "new" ? { new_name: dest.newName.trim() } : {}),
    rows: rows.map((r) => ({
      index: r.index, title: r.title, owner: r.owner, start: r.start, end: r.end, skip: skip.has(r.index),
    })),
  };
}
