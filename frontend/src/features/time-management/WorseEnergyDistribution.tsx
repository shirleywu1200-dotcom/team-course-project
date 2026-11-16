import type { TimeManagementStats } from "../../api/queries";

type Distribution = TimeManagementStats["worse_by_energy"];

function NotDone({ count }: { count: Distribution["not_done"] }) {
  return <div className="card stats-not-done" role="group" aria-label="尚未完成分類">
    <h3>尚未完成</h3><p aria-label="尚未完成">{count} 個任務</p>
    <p className="muted">依端點分類，沒有完成回報的任務歸入此格；此格不是精力等級</p>
  </div>;
}

export function WorseEnergyDistribution({ energy }: { energy: Distribution }) {
  return <section aria-label="被標變差的任務完成時的精力分布">
    <h2>被標變差的任務完成時的精力分布</h2>
    <div className="stats-energy-levels" role="group" aria-label="精力等級">
      <div className="card"><h3>高精力</h3><p aria-label="高精力">{energy.high} 個任務</p></div>
      <div className="card"><h3>中精力</h3><p aria-label="中精力">{energy.mid} 個任務</p></div>
      <div className="card"><h3>低精力</h3><p aria-label="低精力">{energy.low} 個任務</p></div>
    </div>
    <NotDone count={energy.not_done} />
  </section>;
}
