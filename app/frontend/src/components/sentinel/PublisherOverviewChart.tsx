import { PieChart, Pie, Cell, Legend, Tooltip, ResponsiveContainer } from 'recharts';
import type { PublisherOverview } from '../../types/sentinel';

interface PublisherOverviewChartProps {
  overview: PublisherOverview;
}

const COLORS = {
  trusted:    '#4caf50',
  watchlist:  '#ffc107',
  fraudulent: '#e53935',
};

function PublisherOverviewChart({ overview }: PublisherOverviewChartProps) {
  const data = [
    { name: 'Trusted',    value: overview.trusted,    color: COLORS.trusted },
    { name: 'Watchlist',  value: overview.watchlist,  color: COLORS.watchlist },
    { name: 'Fraudulent', value: overview.fraudulent, color: COLORS.fraudulent },
  ];

  return (
    <div className="panel">
      <h3 className="panel-title">Publisher Overview</h3>
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            cx="50%"
            cy="50%"
            innerRadius={52}
            outerRadius={76}
            paddingAngle={2}
          >
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{ background: 'var(--panel-bg)', border: '1px solid var(--border-subtle)', borderRadius: 8 }}
            formatter={(_value, _name, item) => [`${item.value ?? 0}%`]}
          />
          <Legend
            iconType="circle"
            iconSize={10}
            formatter={(value) => <span style={{ color: 'var(--text-primary)', fontSize: '0.85rem' }}>{value}</span>}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

export default PublisherOverviewChart;
