import type { PublisherRow, PublisherStatus } from '../../types/sentinel';

interface PublisherTableProps {
  publishers: PublisherRow[];
  sortBy: string;
  onSortChange: (field: string) => void;
  onShowDetails: (publisher: PublisherRow) => void;
}

const STATUS_SORT_FIELDS = [
  { value: 'trustScore', label: 'Trust Score' },
  { value: 'ctr', label: 'CTR' },
  { value: 'anomalyScore', label: 'Anomaly Score' },
  { value: 'name', label: 'Name' },
];

function statusClass(status: PublisherStatus): string {
  switch (status) {
    case 'Trusted':          return 'trusted';
    case 'Watchlist':        return 'watchlist';
    case 'Suspicious':       return 'suspicious';
    case 'Zero Conversions': return 'zero-conversions';
    case 'Bot-Like Activity':return 'bot-like';
  }
}

function rowIcon(status: PublisherStatus) {
  if (status === 'Bot-Like Activity') return <span className="pub-icon pub-icon--danger">!</span>;
  if (status === 'Zero Conversions') return <span className="pub-icon pub-icon--warn">i</span>;
  return <span className="pub-icon pub-icon--ok">✓</span>;
}

function PublisherTable({ publishers, sortBy, onSortChange, onShowDetails }: PublisherTableProps) {
  return (
    <div className="panel">
      <div className="pub-table-header">
        <h2 className="panel-title">Publisher Trust Scores</h2>
        <div className="pub-table-sort">
          <span className="sort-label">Sort by:</span>
          <select
            className="sort-select"
            value={sortBy}
            onChange={e => onSortChange(e.target.value)}
          >
            {STATUS_SORT_FIELDS.map(f => (
              <option key={f.value} value={f.value}>{f.label}</option>
            ))}
          </select>
        </div>
      </div>

      <table className="data-table">
        <thead>
          <tr>
            <th></th>
            <th>Publisher</th>
            <th>Trust Score</th>
            <th>CTR</th>
            <th>CVR</th>
            <th>Anomaly Score</th>
            <th>Status</th>
            <th>Last Alert</th>
          </tr>
        </thead>
        <tbody>
          {publishers.map(pub => (
            <tr key={pub.id}>
              <td>{rowIcon(pub.status)}</td>
              <td className="pub-name">{pub.name}</td>
              <td><strong>{pub.trustScore}</strong></td>
              <td>{pub.ctr.toFixed(1)}%</td>
              <td>{pub.cvr.toFixed(1)}%</td>
              <td>
                {pub.anomalyScore >= 0.5 && <span className="anomaly-arrow">▲ </span>}
                {pub.anomalyScore.toFixed(2)}
              </td>
              <td>
                <span className={`status-badge status-badge--${statusClass(pub.status)}`}>
                  {pub.status}
                </span>
              </td>
              <td className="last-alert">{pub.lastAlert || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="pub-table-footer">
        <span className="sort-label">Sort by: <strong>{STATUS_SORT_FIELDS.find(f => f.value === sortBy)?.label}</strong></span>
        <button
          className="btn btn--inline"
          onClick={() => publishers.length > 0 && onShowDetails(publishers[0])}
        >
          Show Details &rsaquo;
        </button>
      </div>
    </div>
  );
}

export default PublisherTable;
