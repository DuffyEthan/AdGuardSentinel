import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import type { TrustBucket } from '../../types/sentinel';

interface TrustDistributionChartProps {
  data: TrustBucket[];
}

// Gradient from red (low trust) to green (high trust) across buckets
const BUCKET_COLORS = ['#e53935', '#fb8c00', '#fdd835', '#8bc34a', '#43a047', '#2e7d32'];

function TrustDistributionChart({ data }: TrustDistributionChartProps) {
  return (
    <div className="panel">
      <h3 className="panel-title">Trust Score Distribution</h3>
      <div className="chart-container chart-container--sm">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 8, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" strokeOpacity={0.6} />
            <XAxis dataKey="range" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
            <YAxis tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} allowDecimals={false} />
            <Tooltip
              contentStyle={{ background: 'var(--panel-bg)', border: '1px solid var(--border-subtle)', borderRadius: 8 }}
              labelStyle={{ color: 'var(--text-primary)' }}
            />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {data.map((_entry, index) => (
                <Cell key={index} fill={BUCKET_COLORS[index % BUCKET_COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default TrustDistributionChart;
