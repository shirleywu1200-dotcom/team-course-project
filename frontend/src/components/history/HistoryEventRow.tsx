import type { components } from "../../api/types.generated";
import { SourceEvidence } from "./SourceEvidence";

export type HistoryItem = components["schemas"]["HistoryItemOut"];
const markLabels = { better: "變好", worse: "變差", none: "不計入" };

export function HistoryEventRow({ item, onAnnotate }: {
  item: HistoryItem;
  onAnnotate?: (item: HistoryItem) => void;
}) {
  const canAnnotate = item.kind === "due" && item.mine && item.delta_days !== null && item.delta_days !== 0;
  return <li className="card">
    <h3>{item.task_title}</h3>
    <p><time dateTime={item.ts}>{item.ts}</time> · {item.actor} · {item.mine ? "我的任務" : "他人的任務"}</p>
    {item.project_name && <p>專案：{item.project_name}</p>}
    <p>事件：{item.kind}／{item.field} · {item.from_value ?? "—"} → {item.to_value ?? "—"}</p>
    {item.delta_days !== null && <p>差距：{item.delta_days} 天</p>}
    {item.mark && <p>原註記：{markLabels[item.mark]}</p>}
    {item.effective_mark && <p>有效註記：{markLabels[item.effective_mark]}</p>}
    {item.reason && <p>原因：{item.reason}</p>}
    {item.note && <p>備註：{item.note}</p>}
    <SourceEvidence source={item.source} />
    {canAnnotate && onAnnotate && <button type="button" onClick={() => onAnnotate(item)}>
      {item.effective_mark === null ? "補註記" : "改註記"}
    </button>}
  </li>;
}
