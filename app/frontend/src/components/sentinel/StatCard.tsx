interface StatCardProps {
  label: string;
  value: string | number;
  variant?: 'teal' | 'orange' | 'red';
}

function StatCard({ label, value, variant = 'teal' }: StatCardProps) {
  return (
    <div className={`stat-card stat-card--${variant}`}>
      <div className="stat-card__label">{label}</div>
      <div className="stat-card__value">{value}</div>
    </div>
  );
}

export default StatCard;
