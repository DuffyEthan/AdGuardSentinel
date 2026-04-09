import { useState } from 'react';
import { useSentinelData } from '../../context/SentinelDataContext';
import type { PublisherRow, PublisherStatus } from '../../types/sentinel';

interface PublisherTableProps {
  onShowDetails: (publisher: PublisherRow) => void;
}

const SORT_FIELDS = [
  { value: 'trustScore', label: 'Trust Score' },
  { value: 'ctr',        label: 'CTR' },
  { value: 'anomalyScore', label: 'Anomaly Score' },
  { value: 'name',       label: 'Name' },
];

function statusClass(status: PublisherStatus): string {
  switch (status) {
    case 'Trusted':          return 'trusted';
    case 'Watchlist':        return 'watchlist';
    case 'CTR Fraud':
    case 'Impression Fraud':
    case 'Click Injection':
    case 'Fraud':            return 'fraud';
  }
}

function rowIcon(status: PublisherStatus) {
  if (status === 'Trusted') return <span className="pub-icon pub-icon--ok">✓</span>;
  if (status === 'Watchlist') return <span className="pub-icon pub-icon--warn">i</span>;
  return <span className="pub-icon pub-icon--danger">!</span>;
}

function PublisherTable({ onShowDetails }: PublisherTableProps) {
  const { publishers } = useSentinelData();
  const [sortBy, setSortBy] = useState('trustScore');

  const sorted = [...publishers].sort((a, b) => {
    if (sortBy === 'name') return a.name.localeCompare(b.name);
    const aVal = a[sortBy as keyof PublisherRow] as number;
    const bVal = b[sortBy as keyof PublisherRow] as number;
    return bVal - aVal;
  });

  return (
    <div className="panel">
      <div className="pub-table-header">
        <h2 className="panel-title">Publisher Trust Scores</h2>
        <div className="pub-table-sort">
          <span className="sort-label">Sort by:</span>
          <select
            className="sort-select"
            value={sortBy}
            onChange={e => setSortBy(e.target.value)}
          >
            {SORT_FIELDS.map(f => (
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
          </tr>
        </thead>
        <tbody>
          {sorted.map(pub => (
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
            </tr>
          ))}
        </tbody>
      </table>

      <div className="pub-table-footer">
        <span className="sort-label">Sort by: <strong>{SORT_FIELDS.find(f => f.value === sortBy)?.label}</strong></span>
        <button
          className="btn btn--inline"
          onClick={() => sorted.length > 0 && onShowDetails(sorted[0])}
        >
          Show Details &rsaquo;
        </button>
      </div>
    </div>
  );
}

export default PublisherTable;
