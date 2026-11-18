import type { TimeManagementStats } from "../../api/queries";
import { ErrorBanner } from "../../components/ErrorBanner";
import { Counts } from "./Counts";
import { JudgementSection } from "./JudgementSection";
import { WorseEnergyDistribution } from "./WorseEnergyDistribution";

interface Props {
  data: TimeManagementStats | undefined;
  isPending: boolean;
  isFetching: boolean;
  error: unknown;
  onRetry: () => void;
}

export function TimeManagementResults({ data, isPending, isFetching, error, onRetry }: Props) {
  if (error) return <section aria-label="統計讀取錯誤"><ErrorBanner error={error} />
    <button type="button" onClick={onRetry}>重試</button></section>;
  if (isPending || !data) return <p role="status">載入統計中</p>;
  // 只辨識全零空態，不加總樣本，也不據此判讀；結論是否顯示只依 judgement。
  const empty = [data.better.count, data.better.days, data.worse.count, data.worse.days,
    data.none, data.unmarked, ...Object.values(data.worse_by_energy)].every(value => value === 0);
  return <div aria-busy={isFetching}>
    {isFetching && <p role="status">更新統計中</p>}
    {empty && <p>目前範圍無統計資料</p>}
    <Counts stats={data} />
    <JudgementSection stats={data} />
    <WorseEnergyDistribution energy={data.worse_by_energy} />
  </div>;
}
