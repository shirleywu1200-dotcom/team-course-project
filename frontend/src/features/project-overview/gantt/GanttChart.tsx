import type { components } from "../../../api/types.generated";

type GanttOut = components["schemas"]["GanttOut"];

export interface GanttChartProps {
  gantt: GanttOut;
  width?: number;
  rowHeight?: number;
  leftLabelWidth?: number;
  dayWidth?: number;
}

const statusText = { todo: "待辦", doing: "進行中", done: "已完成" };
const headerHeight = 48;
const footerHeight = 24;
const rightPadding = 24;

// 日期字串只轉為等距日座標；不讀取時鐘、不格式化／換算顯示時區。
function dayCoordinate(date: string) {
  return Date.parse(`${date}T00:00:00Z`) / 86_400_000;
}

function differenceText(deltaDays: number) {
  if (deltaDays < 0) return `提前 ${Math.abs(deltaDays)} 天`;
  if (deltaDays > 0) return `延後 ${deltaDays} 天`;
  return "與原訂同日";
}

/** 純 SVG 展示；不讀 API、快取、系統日期，也不接收操作回呼。 */
export function GanttChart({
  gantt, width, rowHeight = 64, leftLabelWidth = 280, dayWidth = 28,
}: GanttChartProps) {
  const svgStyle = { fontFamily: "var(--font-sans)", fontSize: "var(--font-size)" };
  if (gantt.range === null || gantt.rows.length === 0) {
    return (
      <svg role="img" aria-label="專案甘特圖" width={width ?? 600} height={80} style={svgStyle}>
        <text x={12} y={40} fill="var(--color-text)">此專案尚無可繪製的時間資料</text>
      </svg>
    );
  }

  const { from, to } = gantt.range;
  const firstDay = dayCoordinate(from);
  const days = Math.max(1, dayCoordinate(to) - firstDay);
  const chartWidth = width ?? leftLabelWidth + days * dayWidth + rightPadding;
  const plotWidth = Math.max(1, chartWidth - leftLabelWidth - rightPadding);
  const chartHeight = headerHeight + gantt.rows.length * rowHeight + footerHeight;
  const bottom = chartHeight - footerHeight;
  const x = (date: string) => leftLabelWidth + (dayCoordinate(date) - firstDay) / days * plotWidth;

  return (
    <svg role="img" aria-label="專案甘特圖" width={chartWidth} height={chartHeight}
      viewBox={`0 0 ${chartWidth} ${chartHeight}`} style={svgStyle}>
      <desc>實心條為進行區間，虛線框為原訂基準，延後段附天數，圓點為完成日；直線為今天。</desc>
      <text x={leftLabelWidth} y={22} fill="var(--color-text)">{from}</text>
      <text x={chartWidth - rightPadding} y={22} textAnchor="end" fill="var(--color-text)">{to}</text>
      <line aria-label={`時間軸 ${from} 至 ${to}`} x1={leftLabelWidth} x2={chartWidth - rightPadding}
        y1={40} y2={40} stroke="var(--color-muted)" />
      {gantt.rows.map((task, index) => {
        const top = headerHeight + index * rowHeight;
        const center = top + rowHeight / 2;
        const startX = x(task.start);
        const origX = x(task.orig_due);
        const end = task.status === "done" && task.done_date !== null ? task.done_date : task.latest_due;
        const endX = x(end);
        const difference = differenceText(task.delta_days);
        const detail = `${statusText[task.status]}，${difference}${task.blocked ? "，阻塞" : ""}`;
        return (
          <g key={task.task_id} role="group" aria-label={`${task.title}，${task.owner}，${detail}`}>
            <title>{task.title}，{task.owner}，{detail}</title>
            <text x={8} y={center - 6} fill="var(--color-text)">{task.title}</text>
            <text x={8} y={center + 14} fill="var(--color-text)">{detail}</text>
            <rect aria-label={`進行區間 ${task.start} 至 ${end}`}
              x={Math.min(startX, endX)} y={center - 4} width={Math.max(1, Math.abs(endX - startX))}
              height={8} fill="var(--color-accent)" />
            {task.latest_due > task.orig_due && (
              <rect aria-label={`延後區間 ${task.orig_due} 至 ${task.latest_due}，${difference}`}
                x={origX} y={center - 4} width={x(task.latest_due) - origX} height={8}
                fill="var(--color-warn-text)" stroke="var(--color-text)" />
            )}
            {/* 基準輪廓與刻線最後繪出，與條帶分離，延後段不會蓋住原訂位置。 */}
            <rect aria-label={`原訂基準框 ${task.start} 至 ${task.orig_due}`}
              x={Math.min(startX, origX)} y={center - 10} width={Math.max(1, Math.abs(origX - startX))}
              height={20} fill="none" stroke="var(--color-text)" strokeDasharray="4 2" />
            <line aria-label={`原訂日 ${task.orig_due}`} x1={origX} x2={origX}
              y1={center - 13} y2={center + 13} stroke="var(--color-text)" strokeWidth={2} />
            {task.status === "done" && task.done_date !== null && (
              <circle aria-label={`完成日 ${task.done_date}`} cx={x(task.done_date)} cy={center} r={5}
                fill="var(--color-ok-text)" stroke="var(--color-text)" />
            )}
          </g>
        );
      })}
      <line aria-label={`今天 ${gantt.today}`} x1={x(gantt.today)} x2={x(gantt.today)}
        y1={30} y2={bottom} stroke="var(--color-error-text)" strokeWidth={2} strokeDasharray="6 3" />
      <text x={8} y={chartHeight - 6} fill="var(--color-text)">實心：進行　虛線框／刻線：原訂　圓點：完成　直線：今天</text>
    </svg>
  );
}
