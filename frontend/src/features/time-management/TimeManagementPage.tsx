import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { fetchTimeManagement } from "../../api/queries";
import { keys, normalizeTimeManagementFilter, type StatsFilter } from "../../api/queryKeys";
import { StatsDateFilter, isReversedRange } from "./StatsDateFilter";
import { TimeManagementResults } from "./TimeManagementResults";
import "./time-management.css";

export function TimeManagementPage() {
  const [search, setSearch] = useSearchParams();
  const filter = normalizeTimeManagementFilter({ from: search.get("from") ?? undefined, to: search.get("to") ?? undefined });
  const invalidRange = isReversedRange(filter);
  const stats = useQuery({ queryKey: keys.timeManagement(filter), queryFn: () => fetchTimeManagement(filter), enabled: !invalidRange });

  function apply(next: StatsFilter) {
    const normalized = normalizeTimeManagementFilter(next);
    const params = new URLSearchParams(search);
    params.delete("from"); params.delete("to");
    if (normalized.from) params.set("from", normalized.from);
    if (normalized.to) params.set("to", normalized.to);
    setSearch(params);
  }

  return <main className="time-management-page">
    <h1>時間管理統計</h1>
    <StatsDateFilter key={`${filter.from ?? ""}/${filter.to ?? ""}`} filter={filter} onApply={apply} />
    {!invalidRange && <TimeManagementResults data={stats.data} isPending={stats.isPending}
      isFetching={stats.isFetching} error={stats.error} onRetry={() => { void stats.refetch(); }} />}
  </main>;
}
