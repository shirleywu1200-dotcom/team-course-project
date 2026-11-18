import { HistoryEventRow, type HistoryItem } from "./HistoryEventRow";

export function HistoryEventList({ items, onAnnotate, onOpenTask, onOpenProjectHistory, onBatchFilter }: {
  items: HistoryItem[];
  onAnnotate?: (item: HistoryItem) => void;
  onOpenTask?: (item: HistoryItem) => void;
  onOpenProjectHistory?: (item: HistoryItem) => void;
  onBatchFilter?: (item: HistoryItem) => void;
}) {
  return <ol>{items.map(item => <HistoryEventRow key={item.id} item={item} onAnnotate={onAnnotate}
    onOpenTask={onOpenTask} onOpenProjectHistory={onOpenProjectHistory} onBatchFilter={onBatchFilter} />)}</ol>;
}
