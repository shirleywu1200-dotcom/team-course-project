// 12.7 診斷結果（D-1）：表格唯讀，診斷只顯示後端回的 issues；錯誤列只能勾略過，要補正就改原文重新預覽。

import type { ImportPreview } from "../../api/types";

const rowNo = (index: number) => index + 1;

interface Props {
  preview: ImportPreview;
  skip: Set<number>;
  onToggleSkip: (index: number) => void;
}

export function DiagnoseTable({ preview, skip, onToggleSkip }: Props) {
  const warns = preview.rows.filter((r) => r.issues.some((i) => i.level === "warn")).length;

  return (
    <section className="card" aria-label="診斷結果">
      <h2>診斷結果</h2>
      <p>
        <span className="tag tag-ok">可匯入 {preview.summary.importable}</span>{" "}
        <span className="tag tag-error">錯誤 {preview.summary.blocking}</span>{" "}
        <span className="tag tag-warn">注意 {warns}</span>{" "}
        <span className="muted">錯誤列不匯入也不猜測，請勾略過或回原文修正。</span>
      </p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr><th>列</th><th>任務</th><th>負責人</th><th>開始</th><th>結束</th><th>診斷</th><th>略過</th></tr>
          </thead>
          <tbody>
            {preview.rows.map((r) => (
              <tr key={r.index} className={r.blocking && !skip.has(r.index) ? "row-error" : undefined}>
                <td>{rowNo(r.index)}</td>
                <td>{r.title}</td>
                <td>{r.owner}</td>
                <td className="nowrap">{r.start ?? "—"}</td>
                <td className="nowrap">{r.end ?? "—"}</td>
                <td>
                  {r.issues.map((i) => (
                    <span key={i.code} className={`tag tag-${i.level}`}>{i.message}</span>
                  ))}
                </td>
                <td>
                  {r.blocking && (
                    <input type="checkbox" aria-label={`略過第 ${rowNo(r.index)} 列`} checked={skip.has(r.index)}
                      onChange={() => onToggleSkip(r.index)} />
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
