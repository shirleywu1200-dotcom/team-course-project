// 11.5 正式共用元件，保留原有 props 與行為。

import type { AdjustDue, Mark } from "../api/types";
import { ExternalReasonHint } from "./ExternalReasonHint";

export type MarkValue = Mark | "defer" | null;

const OPTIONS: { value: Exclude<MarkValue, null>; label: string }[] = [
  { value: "better", label: "變好" },
  { value: "worse", label: "變差" },
  { value: "none", label: "不計入" },
  { value: "defer", label: "稍後註記" },
];

interface Props {
  name: string;
  value: MarkValue;
  onChange: (v: MarkValue) => void;
  externalHint?: boolean;
}

export function MarkChoice({ name, value, onChange, externalHint = false }: Props) {
  return (
    <fieldset className="field">
      <legend>要計入時間管理嗎？</legend>
      <div className="choices">
        {OPTIONS.map((o) => (
          <label key={o.value} className="choice">
            <input
              type="radio"
              name={name}
              value={o.value}
              checked={value === o.value}
              onChange={() => onChange(o.value)}
            />
            {o.label}
          </label>
        ))}
      </div>
      {externalHint && <ExternalReasonHint />}
    </fieldset>
  );
}

export function markPayload(v: MarkValue): Pick<AdjustDue, "mark" | "defer_mark"> {
  return v === "defer" || v === null ? { mark: null, defer_mark: v === "defer" } : { mark: v, defer_mark: false };
}
