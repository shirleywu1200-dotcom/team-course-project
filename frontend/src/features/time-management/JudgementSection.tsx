import type { TimeManagementStats } from "../../api/queries";

function JudgementNote({ note }: { note: TimeManagementStats["judgement_note"] }) {
  return <p className="stats-server-text">{note}</p>;
}

export function JudgementSection({ stats }: { stats: TimeManagementStats }) {
  return <section className="card" aria-label="判讀與說明">
    {stats.judgement !== null && <><h2>判讀結論</h2><p className="stats-server-text">{stats.judgement}</p></>}
    <JudgementNote note={stats.judgement_note} />
  </section>;
}
