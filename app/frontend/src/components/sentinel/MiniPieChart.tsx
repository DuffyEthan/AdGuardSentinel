import { PieChart, Pie, Cell, Tooltip } from 'recharts';
import type { MiniPieSegment } from '../../types/sentinel';

interface MiniPieChartProps {
  segments: MiniPieSegment[];
  size?: number;
}

function MiniPieChart({ segments, size = 90 }: MiniPieChartProps) {
  return (
    <div className="mini-pie-wrapper">
      <PieChart width={size} height={size}>
        <Pie
          data={segments}
          dataKey="value"
          cx="50%"
          cy="50%"
          outerRadius={size / 2 - 4}
          strokeWidth={1}
        >
          {segments.map((seg, i) => (
            <Cell key={i} fill={seg.color} />
          ))}
        </Pie>
        <Tooltip
          formatter={(_value, _name, entry: { payload?: MiniPieSegment }) =>
            [(entry.payload?.value ?? ''), (entry.payload?.label ?? '')]
          }
        />
      </PieChart>
      <div className="mini-pie-labels">
        {segments.map((seg, i) => (
          seg.label ? (
            <span key={i} className="mini-pie-label">
              <span className="mini-pie-dot" style={{ background: seg.color }} />
              {seg.label}
            </span>
          ) : null
        ))}
      </div>
    </div>
  );
}

export default MiniPieChart;
