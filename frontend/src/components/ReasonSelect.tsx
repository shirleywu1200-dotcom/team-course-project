// 11.5 正式共用元件，保留原有 props 與行為。

import type { Direction, DueReason } from "../api/types";
import { ExternalReasonHint } from "./ExternalReasonHint";

interface Props {
  id: string;
  reasons: DueReason[];
  direction: Direction | null;
  value: string;
  onChange: (code: string) => void;
  showExternalHint?: boolean;
}

export function ReasonSelect({ id, reasons, direction, value, onChange, showExternalHint = true }: Props) {
  const options = direction ? reasons.filter((r) => r.direction === direction) : [];
  return (
    <div className="field">
      <label htmlFor={id}>原因</label>
      <select id={id} value={value} disabled={!direction} onChange={(e) => onChange(e.target.value)}>
        <option value="">請選擇原因</option>
        {options.map((r) => (
          <option key={`${r.direction}-${r.code}`} value={r.code}>
            {r.label}
          </option>
        ))}
      </select>
      {showExternalHint && isExternal(reasons, direction, value) && <ExternalReasonHint />}
    </div>
  );
}

export function isExternal(reasons: DueReason[], direction: Direction | null, code: string): boolean {
  return reasons.some((r) => r.direction === direction && r.code === code && r.external);
}
