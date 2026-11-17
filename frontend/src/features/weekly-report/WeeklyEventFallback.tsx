import { Link } from "react-router-dom";

import type { WeeklyItem } from "./weeklyRequests";

const sections = [
  ["done", "本週完成"], ["delay", "延期事項"], ["next", "下週重點與風險"],
] as const;

function Item({ item }: { item: WeeklyItem }) {
  return <li>
    <Link to={`/tasks/${item.task_id}`}>{item.title ?? `任務 #${item.task_id}`}</Link>
    {item.owner && <span> · {item.owner}</span>}
    {item.done_date && <span> · 完成日 {item.done_date}</span>}
    {item.orig_due && <span> · 原訂 {item.orig_due}</span>}
    {item.latest_due && <span> · 最新 {item.latest_due}</span>}
    {item.blocked && <span> · 已卡住</span>}
    {item.event && <small className="weekly-evidence">事件 #{item.event.id} · {item.event.ts}
      {item.event.from_value !== null && <> · 事件前值 {item.event.from_value}</>}
      {item.event.to_value !== null && <> · 事件後值 {item.event.to_value}</>}
      {item.event.delta_days !== null && <> · 延後 {item.event.delta_days} 天</>}
    </small>}
  </li>;
}

export function WeeklyEventFallback({ items }: { items: WeeklyItem[] }) {
  if (items.length === 0) return <p>本週沒有可列的工作項目。</p>;
  return <div className="weekly-items">
    {sections.map(([section, title]) => {
      const listed = items.filter((item) => item.section === section);
      if (listed.length === 0) return null;
      return <section key={section} aria-label={title}>
        <h3>{title}</h3>
        <ul>{listed.map((item) => <Item key={`${item.section}-${item.task_id}-${item.event_id}`} item={item} />)}</ul>
      </section>;
    })}
  </div>;
}
