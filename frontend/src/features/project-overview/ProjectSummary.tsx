import type { components } from "../../api/types.generated";

type GanttSummary = components["schemas"]["GanttSummary"];

export function ProjectSummary({ summary }: { summary: GanttSummary }) {
  return <div className="project-summary">
    <section className="card" aria-label="正式任務摘要">
      <h2>任務摘要</h2>
      <p>已完成 {summary.done}／{summary.total}</p>
      <p>已延期 {summary.delayed}</p>
    </section>
    <section className="card" aria-label="待確認候選">
      <h2>待確認候選</h2>
      <p>已對應本專案的待確認候選：{summary.open_candidates}</p>
      <p className="muted">不計入正式任務與甘特圖。</p>
    </section>
  </div>;
}
