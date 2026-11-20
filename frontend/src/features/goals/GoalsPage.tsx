import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../../api/client";
import { keys } from "../../api/queryKeys";
import type { components } from "../../api/types.generated";
import { GoalEnergyMatrix } from "./GoalEnergyMatrix";
import { GoalLinkInbox } from "./GoalLinkInbox";
import { GoalManagement } from "./GoalManagement";
import { GoalStatsSection } from "./GoalStatsSection";

type GoalListOut = components["schemas"]["GoalListOut"];

export function GoalsPage() {
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const goals = useQuery({ queryKey: keys.goals(),
    queryFn: () => api<GoalListOut>("/goals?include_archived=true") });
  const selectedGoalId = selectedId ?? goals.data?.items[0]?.id ?? null;
  return <main className="wide">
    <h1>目標與精力</h1>
    <p className="muted">預期精力用於自我規劃，實際精力由使用者在完成回報時自評。</p>
    <GoalManagement goals={goals.data?.items} loading={!goals.data && !goals.error} error={goals.error}
      onRetry={() => { void goals.refetch(); }} selectedId={selectedGoalId} onSelect={setSelectedId} />
    <GoalStatsSection goalId={selectedGoalId} />
    <GoalEnergyMatrix />
    <GoalLinkInbox goals={goals.data?.items} />
  </main>;
}
