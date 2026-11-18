import { HistoryEventRow, type HistoryItem } from "./HistoryEventRow";

export function HistoryEventList({ items, onAnnotate }: {
  items: HistoryItem[];
  onAnnotate?: (item: HistoryItem) => void;
}) {
  return <ol>{items.map(item => <HistoryEventRow key={item.id} item={item} onAnnotate={onAnnotate} />)}</ol>;
}
