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
import { renderAnomalyAreas } from './AnomalyArea';
import type { AnomalyEvent } from './AnomalyArea';

interface DataPoint {
  x: number; // Unix ms timestamp
  impression_count: number;
  click_count: number;
  conversion_count: number;
}

interface TimeSeriesChartProps {
  data: DataPoint[];
  publisher: string;
  anomalies?: AnomalyEvent[];
}

function TimeSeriesChart({ data, publisher, anomalies = [] }: TimeSeriesChartProps) {
  const { theme } = useTheme();

  const colors = theme === 'light'
    ? {
        title: '#0d7377',
        grid: '#b0bec5',
        axis: '#5a6a7a',
        line1: '#14919b',
        line2: '#aaaa80',
        line3: '#91149b',
        dot: '#0d7377',
        tooltipBg: '#ffffff',
        tooltipBorder: 'rgba(0,0,0,0.1)',
        tooltipText: '#1a2a3a',
      }
    : {
        title: '#7dd3d9',
        grid: '#4a5a6a',
        axis: '#a0b0c0',
        line1: '#5ec4cc',
        line2: '#ccc45e',
        line3: '#c45ecc',
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
        {publisher} — Impressions, Clicks &amp; Conversions
      </h3>
      <ResponsiveContainer width="100%" height="78%">
        <LineChart data={data} margin={{ top: 40, right: 30, left: 20, bottom: 30 }}>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke={colors.grid}
            strokeOpacity={0.5}
            vertical={false}
          />
          <XAxis
            dataKey="x"
            type="number"
            scale="time"
            domain={['dataMin', 'dataMax']}
            stroke={colors.axis}
            tick={{ fill: colors.axis, fontSize: 12 }}
            tickCount={8}
            tickFormatter={(value) => new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            label={{ value: 'Time', position: 'bottom', fill: colors.axis, offset: 10 }}
          />
          <YAxis
            scale="log"
            domain={[1, (max: number) => max * 2]}
            stroke={colors.axis}
            tick={{ fill: colors.axis, fontSize: 12 }}
            allowDataOverflow
            label={{ value: 'Count (log)', angle: -90, position: 'insideLeft', fill: colors.axis }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: colors.tooltipBg,
              border: `1px solid ${colors.tooltipBorder}`,
              borderRadius: '8px',
              color: colors.tooltipText
            }}
            formatter={(value, name) => {
              const labels: Record<string, string> = {
                impression_count: 'Impressions',
                click_count: 'Clicks',
                conversion_count: 'Conversions',
              };
              return [(value as number).toFixed(0), labels[name as string] ?? name];
            }}
            labelFormatter={(label) => new Date(label as number).toLocaleString()}
          />
          {renderAnomalyAreas(anomalies)}
          <Line
            type="monotone"
            dataKey="impression_count"
            stroke={colors.line1}
            strokeWidth={2.5}
            dot={false}
            isAnimationActive={false}
            activeDot={{ r: 4, fill: colors.dot }}
          />
          <Line
            type="monotone"
            dataKey="click_count"
            stroke={colors.line2}
            strokeWidth={2.5}
            dot={false}
            isAnimationActive={false}
            activeDot={{ r: 4, fill: colors.dot }}
          />
          <Line
            type="monotone"
            dataKey="conversion_count"
            stroke={colors.line3}
            strokeWidth={2.5}
            dot={false}
            isAnimationActive={false}
            activeDot={{ r: 4, fill: colors.dot }}
          />
        </LineChart>
      </ResponsiveContainer>
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        gap: '24px',
        marginTop: '6px',
        fontSize: 12,
        color: colors.axis,
      }}>
        {([
          { color: colors.line1, label: 'Impressions' },
          { color: colors.line2, label: 'Clicks' },
          { color: colors.line3, label: 'Conversions' },
        ] as { color: string; label: string }[]).map(({ color, label }) => (
          <span key={label} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <svg width="28" height="4" style={{ flexShrink: 0 }}>
              <line x1="0" y1="2" x2="28" y2="2" stroke={color} strokeWidth="2.5" />
            </svg>
            {label}
          </span>
        ))}
      </div>
    </div>
  );
}

export default TimeSeriesChart;
