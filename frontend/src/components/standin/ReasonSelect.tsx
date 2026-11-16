// 暫代 Dev-C todo 11.5「原因下拉（外部原因顯示提示）」。Phase 11 完成後改用共用元件。
// 手刻原因：Phase 11 共用元件尚未建立。只列出該方向的原因，預設不選（FR-DUE-05a）。

import type { Direction, DueReason } from "../../api/types";

interface Props {
  id: string;
  reasons: DueReason[];
  direction: Direction | null;
  value: string;
  onChange: (code: string) => void;
}

export function ReasonSelect({ id, reasons, direction, value, onChange }: Props) {
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
    </div>
  );
}

export function isExternal(reasons: DueReason[], direction: Direction | null, code: string): boolean {
  return reasons.some((r) => r.direction === direction && r.code === code && r.external);
}
