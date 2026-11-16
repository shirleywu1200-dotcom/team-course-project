import type { TimeManagementStats } from "../../api/queries";

export function Counts({ stats }: { stats: TimeManagementStats }) {
  return <section aria-label="時間管理計數">
    <h2>時間管理計數</h2>
    <div className="stats-count-grid">
      <div className="card"><h3>變好</h3><dl className="summary">
        <dt>變好次數</dt><dd aria-label="變好次數">{stats.better.count} 次</dd>
        <dt>提前總天數</dt><dd aria-label="提前總天數">{stats.better.days} 天</dd>
      </dl></div>
      <div className="card"><h3>變差</h3><dl className="summary">
        <dt>變差次數</dt><dd aria-label="變差次數">{stats.worse.count} 次</dd>
        <dt>延後總天數</dt><dd aria-label="延後總天數">{stats.worse.days} 天</dd>
      </dl></div>
      <div className="card"><h3>其他註記</h3><dl className="summary">
        <dt>不計入次數</dt><dd aria-label="不計入次數">{stats.none} 次</dd>
        <dt>未註記次數</dt><dd aria-label="未註記次數">{stats.unmarked} 次</dd>
      </dl></div>
    </div>
  </section>;
}
