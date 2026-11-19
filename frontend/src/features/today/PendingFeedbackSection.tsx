import { Link } from "react-router-dom";
import type { components } from "../../api/types.generated";

type PendingFeedbackItem = components["schemas"]["PendingFeedbackItem"];

function PendingFeedbackRow({ item }: { item: PendingFeedbackItem }) {
  return <li className="card">
    <Link to={`/tasks/${item.task_id}/feedback`}>補填{item.title}回報</Link>
    <p>完成日：{item.done_date} · 原訂日：{item.orig_due} · 逾期 {item.overdue_days} 天</p>
    <p>負責人：{item.owner} · 事前預設星數：{item.expected_stars}</p>
  </li>;
}

export function PendingFeedbackSection({ items }: { items: PendingFeedbackItem[] }) {
  return items.length === 0 ? <p>沒有待補完成回報。</p>
    : <ul>{items.map(item => <PendingFeedbackRow key={item.task_id} item={item} />)}</ul>;
}
