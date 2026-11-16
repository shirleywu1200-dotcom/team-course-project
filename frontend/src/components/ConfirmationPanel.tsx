import { useId, type ReactNode } from "react";

interface Props {
  title: string;
  children: ReactNode;
  canConfirm?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

// FR-BLK-01／FR-BAS-03：呼叫者持有確認條件，面板不自行推論或寫入。
export function ConfirmationPanel({ title, children, canConfirm = false, onConfirm, onCancel }: Props) {
  const titleId = useId();
  return <section className="card" aria-labelledby={titleId}>
    <h2 id={titleId}>{title}</h2>
    {children}
    <div className="actions">
      <button type="button" onClick={onCancel}>取消</button>
      <button type="button" className="primary" disabled={!canConfirm} onClick={onConfirm}>確認</button>
    </div>
  </section>;
}
