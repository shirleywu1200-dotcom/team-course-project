// 12.7 欄位對應（D-2）：rule 不停（收合顯示）；ai 要按「確認對應」；null 要先手動指定任務名稱與結束。
// 下拉只是草稿，按「套用對應」才帶 column_map 重送 preview（後端回 mapped_by="manual"）。

import { useState } from "react";

import type { ColumnIndexes, ImportPreview } from "../../api/types";

const FIELDS: { key: keyof ColumnIndexes; label: string; required: boolean }[] = [
  { key: "title", label: "任務名稱", required: true },
  { key: "owner", label: "負責人", required: false },
  { key: "start", label: "開始", required: false },
  { key: "end", label: "結束", required: true },
];

const SOURCE: Record<string, string> = { rule: "規則對應", ai: "AI 建議", manual: "手動指定" };

interface Props {
  preview: ImportPreview;
  confirmed: boolean;
  busy: boolean;
  onConfirm: () => void;
  onApply: (map: ColumnIndexes) => void;
  privateTarget: boolean;
}

export function MappingPanel({ preview, confirmed, busy, onConfirm, onApply, privateTarget }: Props) {
  const { mapped_by, title, owner, start, end } = preview.column_map;
  // 只保留四欄索引，ai_run_id 是 commit metadata，不能混入 Strict ColumnMap。
  const current = { title, owner, start, end };
  const [draft, setDraft] = useState<ColumnIndexes>(current);
  const changed = FIELDS.some((f) => draft[f.key] !== current[f.key]);
  const complete = draft.title !== null && draft.end !== null;

  return (
    <section className="card" aria-label="欄位對應">
      <div className="head">
        <h2>欄位對應</h2>
        <span className="tag">{mapped_by ? SOURCE[mapped_by] : "需手動指定"}</span>
      </div>
      {mapped_by === null && <p className="hint">{privateTarget
        ? "私人專案不送 AI，請手動指定"
        : "AI 無法判斷欄位，請手動指定任務名稱與結束欄位。"}</p>}
      {mapped_by === "ai" && !confirmed && (
        <p className="hint">表頭不是標準名稱，以下是 AI 的建議。請確認或修改後才能保存。</p>
      )}
      {mapped_by === "ai" && confirmed && <p className="banner banner-ok">對應已確認。</p>}
      <details open={mapped_by !== "rule"}>
        <summary className="muted">
          {FIELDS.map((f) => `${f.label}＝${current[f.key] === null ? "（無）" : preview.header[current[f.key]!]}`).join("、")}
        </summary>
        <div className="map-grid">
          {FIELDS.map((f) => (
            <div className="field" key={f.key}>
              <label htmlFor={`map-${f.key}`}>{f.label}</label>
              <select id={`map-${f.key}`} required={f.required} value={draft[f.key] ?? ""}
                onChange={(e) => setDraft({ ...draft, [f.key]: e.target.value === "" ? null : Number(e.target.value) })}>
                <option value="">（無）</option>
                {preview.header.map((h, i) => (
                  <option key={i} value={i}>{h || `第 ${i + 1} 欄`}</option>
                ))}
              </select>
            </div>
          ))}
        </div>
        <div className="actions">
          {mapped_by === "ai" && (
            <button type="button" className="primary" disabled={confirmed || changed} onClick={onConfirm}>確認對應</button>
          )}
          <button type="button" disabled={!changed || !complete || busy} onClick={() => onApply(draft)}>套用對應</button>
          <span className="muted">改了對應會重新預覽</span>
        </div>
      </details>
    </section>
  );
}
