// 12.8 收件匣分區（SDD 第 2 節）：由候選種類推導，不另存狀態。

import type { Candidate, CandidateKind } from "../../api/types";

export type Zone = "sure" | "unclear" | "unmatched";

export const ZONES: { zone: Zone; title: string }[] = [
  { zone: "sure", title: "待你確認" },
  { zone: "unclear", title: "待釐清" },
  { zone: "unmatched", title: "待配對" },
];

export function zoneOf(kind: CandidateKind): Zone {
  if (kind === "unclear") return "unclear";
  if (kind === "unmatched") return "unmatched";
  return "sure";
}

export function groupCandidates(candidates: Candidate[]): Record<Zone, Candidate[]> {
  const groups: Record<Zone, Candidate[]> = { sure: [], unclear: [], unmatched: [] };
  for (const c of candidates) groups[zoneOf(c.kind)].push(c);
  return groups;
}
