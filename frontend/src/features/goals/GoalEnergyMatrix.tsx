import { useQuery } from "@tanstack/react-query";

import { api } from "../../api/client";
import { keys } from "../../api/queryKeys";
import type { components } from "../../api/types.generated";
import { ErrorBanner } from "../../components/ErrorBanner";

type GoalMatrixOut = components["schemas"]["GoalMatrixOut"];
const energyLabels = { high: "高", mid: "中", low: "低" };

export function GoalEnergyMatrix() {
  const matrix = useQuery({ queryKey: keys.goalMatrix(), queryFn: () => api<GoalMatrixOut>("/goals/matrix") });
  return <section className="card" aria-label="目標精力矩陣">
    <h2>目標精力矩陣</h2>
    {matrix.error ? <><ErrorBanner error={matrix.error} />
      <button type="button" onClick={() => { void matrix.refetch(); }}>重試矩陣</button></>
      : !matrix.data ? <p role="status">載入矩陣中…</p>
        : matrix.data.items.length === 0 ? <p>尚無矩陣資料。</p>
          : <div className="table-scroll"><table>
            <thead><tr><th>目標</th><th>預期精力</th><th>關聯件數</th><th>高</th><th>中</th><th>低</th></tr></thead>
            <tbody>{matrix.data.items.map(item => <tr key={item.goal_id}>
              <th scope="row">{item.title}</th><td>{energyLabels[item.energy_plan]}</td><td>{item.linked}</td>
              <td>{item.energy.high}</td><td>{item.energy.mid}</td><td>{item.energy.low}</td>
            </tr>)}</tbody>
          </table></div>}
  </section>;
}
