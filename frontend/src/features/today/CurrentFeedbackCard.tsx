import { Link } from "react-router-dom";
import type { components } from "../../api/types.generated";

type FeedbackOut = components["schemas"]["FeedbackOut"];
const energyLabels = { high: "高", mid: "中", low: "低" };
const investLabels = { less: "少於預期", as_expected: "如期", more: "多於預期" };

function displayTimestamp(value: string) {
  return value.replace("T", " ").replace(/(\d{2}:\d{2}:\d{2})(?:\.\d+)?(Z|[+-]\d{2}:\d{2})$/, "$1 $2");
}

export function CurrentFeedbackCard({ feedback }: { feedback: FeedbackOut }) {
  return <section className="card" aria-label="目前回報">
    <h2>目前回報</h2>
    <dl>
      <dt>實際達成星數</dt><dd>{feedback.actual_stars} 星</dd>
      <dt>自評精力</dt><dd>{energyLabels[feedback.energy]}</dd>
      <dt>投入相對預期</dt><dd>{feedback.invest_vs_expected ? investLabels[feedback.invest_vs_expected] : "未填寫"}</dd>
      <dt>逾期天數</dt><dd>{feedback.overdue_days} 天</dd>
      <dt>量表版本</dt><dd>{feedback.rubric_id}</dd>
      <dt>儲存時間</dt><dd><time dateTime={feedback.created_at}>{displayTimestamp(feedback.created_at)}</time></dd>
    </dl>
    <p>修改功能尚未開放</p>
    <Link to={`/tasks/${feedback.task_id}`}>查看任務歷程</Link>
  </section>;
}
