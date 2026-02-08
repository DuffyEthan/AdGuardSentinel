import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

interface DataPoint {
  x: number;
  y: number;
}

interface TimeSeriesChartProps {
  data: DataPoint[];
  publisher: string;
}

function TimeSeriesChart({ data, publisher }: TimeSeriesChartProps) {
  return (
    <div className="chart-container">
      <h3 style={{
        color: '#0d7377',
        textAlign: 'center',
        marginBottom: '1rem',
        fontWeight: 700
      }}>
        {publisher} — Time Series: f(x) = 2 + sin(10x)
      </h3>
      <ResponsiveContainer width="100%" height="85%">
        <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 25 }}>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#b0bec5"
            strokeOpacity={0.6}
            vertical={false}
          />
          <XAxis
            dataKey="x"
            stroke="#5a6a7a"
            tick={{ fill: '#5a6a7a', fontSize: 12 }}
            tickFormatter={(value) => value.toFixed(0)}
            label={{ value: 'x', position: 'bottom', fill: '#5a6a7a', offset: 10 }}
          />
          <YAxis
            stroke="#5a6a7a"
            tick={{ fill: '#5a6a7a', fontSize: 12 }}
            domain={[0, 4]}
            label={{ value: 'y', angle: -90, position: 'insideLeft', fill: '#5a6a7a' }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#ffffff',
              border: '1px solid rgba(0,0,0,0.1)',
              borderRadius: '8px',
              color: '#1a2a3a'
            }}
            formatter={(value: number) => [value.toFixed(4), 'y']}
            labelFormatter={(label: number) => `x: ${label.toFixed(2)}`}
          />
          <Line
            type="monotone"
            dataKey="y"
            stroke="#14919b"
            strokeWidth={2.5}
            dot={false}
            activeDot={{ r: 4, fill: '#0d7377' }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default TimeSeriesChart;
