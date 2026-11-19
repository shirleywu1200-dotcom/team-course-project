import { Link } from "react-router-dom";
import type { components } from "../../api/types.generated";

type GanttRow = components["schemas"]["GanttRowOut"];
const statusLabels = { todo: "待辦", doing: "進行中", done: "已完成" };

export function ProjectTaskTable({ rows, onAdjust }: { rows: GanttRow[]; onAdjust: (taskId: number) => void }) {
  if (rows.length === 0) return <p>此專案尚無任務。</p>;
  return <div className="project-task-scroll">
    <table>
      <thead><tr>{["任務", "負責人", "狀態", "開始", "原訂", "最新預計", "與原訂差距", "日期操作"].map(label =>
        <th key={label} scope="col">{label}</th>)}</tr></thead>
      <tbody>{rows.map(row => <tr key={row.task_id}>
        <th scope="row"><Link to={`/tasks/${row.task_id}`}>{row.title}</Link></th>
        <td>{row.owner}</td>
        <td>{statusLabels[row.status]}{row.blocked && <> · <span>已封鎖</span></>}</td>
        <td>{row.start}</td><td>{row.orig_due}</td><td>{row.latest_due}</td>
        <td>{row.delta_days} 天</td>
        <td>{row.status !== "done" && <button type="button" aria-label={`改預計日：${row.title}`} onClick={() => onAdjust(row.task_id)}>改預計日</button>}</td>
      </tr>)}</tbody>
    </table>
  </div>;
}
