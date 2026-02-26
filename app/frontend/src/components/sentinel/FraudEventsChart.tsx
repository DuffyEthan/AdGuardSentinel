import {
  Line, XAxis, YAxis, CartesianGrid, Tooltip, Area, ResponsiveContainer,
  ComposedChart,
} from 'recharts';
import type { FraudEvent } from '../../types/sentinel';

interface FraudEventsChartProps {
  data: FraudEvent[];
}

function FraudEventsChart({ data }: FraudEventsChartProps) {
  return (
    <div className="panel">
      <h3 className="panel-title">Fraud Events (Past 7 Days)</h3>
      <div className="chart-container chart-container--sm">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 8, right: 8, left: -10, bottom: 0 }}>
            <defs>
              <linearGradient id="fraudGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#e8a030" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#e8a030" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" strokeOpacity={0.6} />
            <XAxis dataKey="day" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
            <YAxis tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} allowDecimals={false} />
            <Tooltip
              contentStyle={{ background: 'var(--panel-bg)', border: '1px solid var(--border-subtle)', borderRadius: 8 }}
              labelStyle={{ color: 'var(--text-primary)' }}
            />
            <Area dataKey="events" fill="url(#fraudGradient)" stroke="none" />
            <Line
              dataKey="events"
              stroke="#e8a030"
              strokeWidth={2}
              dot={{ r: 4, fill: '#e8a030', strokeWidth: 0 }}
              activeDot={{ r: 5 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default FraudEventsChart;
