import { useId, useState, type FormEvent } from "react";
import { normalizeTimeManagementFilter, type StatsFilter } from "../../api/queryKeys";
import { DatePicker } from "../../components/DatePicker";

export const RANGE_ERROR = "起日不得晚於迄日。";
export const isReversedRange = (filter: StatsFilter) => Boolean(filter.from && filter.to && filter.from > filter.to);

export function StatsDateFilter({ filter, onApply }: { filter: StatsFilter; onApply: (filter: StatsFilter) => void }) {
  const id = useId();
  const [from, setFrom] = useState(filter.from ?? "");
  const [to, setTo] = useState(filter.to ?? "");
  const [error, setError] = useState(isReversedRange(filter) ? RANGE_ERROR : "");

  function submit(event: FormEvent) {
    event.preventDefault();
    const next = normalizeTimeManagementFilter({ from, to });
    if (isReversedRange(next)) { setError(RANGE_ERROR); return; }
    setError("");
    onApply(next);
  }

  return <form className="card stats-date-filter" aria-label="統計日期範圍" onSubmit={submit}>
    <div className="stats-date-fields">
      <DatePicker id={`${id}-from`} label="起日" value={from} onChange={setFrom} />
      <DatePicker id={`${id}-to`} label="迄日" value={to} onChange={setTo} />
      <button type="submit" className="primary">套用</button>
    </div>
    <p className="muted">日期可留空；兩格皆空時查詢全部。</p>
    {error && <p className="banner banner-error" role="alert">{error}</p>}
  </form>;
}
