import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { useTheme } from '../context/ThemeContext';

interface DataPoint {
  x: number;
  y: number;
}

interface TimeSeriesChartProps {
  data: DataPoint[];
  publisher: string;
}

function TimeSeriesChart({ data, publisher }: TimeSeriesChartProps) {
  const { theme } = useTheme();

  const colors = theme === 'light'
    ? {
        title: '#0d7377',
        grid: '#b0bec5',
        axis: '#5a6a7a',
        line: '#14919b',
        dot: '#0d7377',
        tooltipBg: '#ffffff',
        tooltipBorder: 'rgba(0,0,0,0.1)',
        tooltipText: '#1a2a3a',
      }
    : {
        title: '#7dd3d9',
        grid: '#4a5a6a',
        axis: '#a0b0c0',
        line: '#5ec4cc',
        dot: '#7dd3d9',
        tooltipBg: '#2d3e50',
        tooltipBorder: 'rgba(255,255,255,0.1)',
        tooltipText: '#e8edf2',
      };

  return (
    <div className="chart-container">
      <h3 style={{
        color: colors.title,
        textAlign: 'center',
        marginBottom: '1rem',
        fontWeight: 700,
        transition: 'color 0.3s ease'
      }}>
        {publisher} — Time Series: f(x) = 2 + sin(10x)
      </h3>
      <ResponsiveContainer width="100%" height="85%">
        <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 25 }}>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke={colors.grid}
            strokeOpacity={0.5}
            vertical={false}
          />
          <XAxis
            dataKey="x"
            stroke={colors.axis}
            tick={{ fill: colors.axis, fontSize: 12 }}
            tickFormatter={(value) => value.toFixed(0)}
            label={{ value: 'x', position: 'bottom', fill: colors.axis, offset: 10 }}
          />
          <YAxis
            stroke={colors.axis}
            tick={{ fill: colors.axis, fontSize: 12 }}
            domain={[0, 4]}
            label={{ value: 'y', angle: -90, position: 'insideLeft', fill: colors.axis }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: colors.tooltipBg,
              border: `1px solid ${colors.tooltipBorder}`,
              borderRadius: '8px',
              color: colors.tooltipText
            }}
            formatter={(value: number) => [value.toFixed(4), 'y']}
            labelFormatter={(label: number) => `x: ${label.toFixed(2)}`}
          />
          <Line
            type="monotone"
            dataKey="y"
            stroke={colors.line}
            strokeWidth={2.5}
            dot={false}
            activeDot={{ r: 4, fill: colors.dot }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default TimeSeriesChart;
