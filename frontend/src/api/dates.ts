// 日期只到「日」，以 YYYY-MM-DD 字串表示（spec 8.2）。日曆天相減，不處理工作日。

import type { Direction } from "./types";

function toUtc(d: string): number {
  const [y, m, day] = d.split("-").map(Number);
  return Date.UTC(y, m - 1, day);
}

export function daysBetween(from: string, to: string): number {
  return Math.round((toUtc(to) - toUtc(from)) / 86_400_000);
}

export function addDays(d: string, n: number): string {
  return new Date(toUtc(d) + n * 86_400_000).toISOString().slice(0, 10);
}

export function directionOf(delta: number): Direction {
  return delta < 0 ? "earlier" : "later";
}

export function formatDelta(delta: number): string {
  if (delta === 0) return "不變";
  return delta > 0 ? `延後 ${delta} 天` : `提前 ${-delta} 天`;
}
