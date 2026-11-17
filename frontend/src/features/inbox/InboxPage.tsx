// todo 12.8：收件匣與每日確認（US-09～11；SDD docs/dev-b/12-8-sdd.md）。
// 版面 D-4：單欄由上到下＝頁首計數 → 貼上 → 待你確認 → 待釐清 → 待配對 → 已處理。
// 「已處理」只列本頁這次處理過的項目（含待補的註記），重新整理後清空。

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { fetchCandidates, fetchSettings, keys } from "../../api/queries";
import type { DecideResult } from "../../api/types";
import { ErrorBanner } from "../../components/ErrorBanner";
import { CandidateCard } from "./CandidateCard";
import { DecidedItem } from "./DecidedItem";
import { groupCandidates, ZONES } from "./group";
import { PasteBox, POLL_LIMIT_MS, POLL_MS } from "./PasteBox";

interface Props {
  pollMs?: number;
  pollLimitMs?: number;
}

export function InboxPage({ pollMs = POLL_MS, pollLimitMs = POLL_LIMIT_MS }: Props) {
  const open = useQuery({ queryKey: keys.candidates("open"), queryFn: () => fetchCandidates("open") });
  const settings = useQuery({ queryKey: keys.settings, queryFn: fetchSettings });
  const [decided, setDecided] = useState<DecideResult[]>([]);

  const items = open.data ?? [];
  const groups = groupCandidates(items);

  return (
    <main>
      <div className="head">
        <h1>收件匣</h1>
        <span>
          {open.isSuccess && <b>待確認 {items.length} 項</b>}
          {settings.data && <span className="muted">　確認時間上限 {settings.data.confirm_cap_min} 分鐘</span>}
        </span>
      </div>
      <PasteBox pollMs={pollMs} pollLimitMs={pollLimitMs} />
      <ErrorBanner error={open.error} />

      {open.isSuccess && items.length === 0 && (
        <p className="card muted">目前沒有待確認項目。確認前，任何狀態與甘特圖都不會改變。</p>
      )}
      {ZONES.filter(({ zone }) => groups[zone].length > 0).map(({ zone, title }) => (
        <section key={zone} aria-labelledby={`zone-${zone}`}>
          <h2 id={`zone-${zone}`}>
            {title} <span className="muted">{groups[zone].length}</span>
          </h2>
          {groups[zone].map((c) => (
            <CandidateCard key={c.id} candidate={c} onDecided={(r) => setDecided((d) => [r, ...d])} />
          ))}
        </section>
      ))}

      {decided.length > 0 && (
        <section aria-labelledby="zone-decided">
          <h2 id="zone-decided">
            已處理 <span className="muted">{decided.length}</span>
          </h2>
          {decided.map((r) => (
            <DecidedItem key={r.candidate.id} result={r} />
          ))}
        </section>
      )}
    </main>
  );
}
