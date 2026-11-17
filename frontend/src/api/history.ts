import { api } from "./client";
import { normalizeEventFilters, type EventFilter } from "./queryKeys";
import type { components } from "./types.generated";

type HistoryList = components["schemas"]["HistoryListOut"];

export function fetchHistory(input: EventFilter): Promise<HistoryList> {
  const filters = normalizeEventFilters(input);
  const search = new URLSearchParams(Object.entries(filters).map(([key, value]) => [key, String(value)]));
  return api<HistoryList>(`/events?${search.toString()}`);
}
