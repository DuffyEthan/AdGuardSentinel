import { useNavigate } from 'react-router-dom';
import type { PublisherStatus } from '../types/sentinel';

interface PublisherCampaignRow {
  publisher: string;
  campaign: string;
  trustScore: number;
  ctr: number;
  anomalyScore: number;
  status: PublisherStatus;
}

const DEMO_ROWS: PublisherCampaignRow[] = [
  { publisher: 'SPY', campaign: 'Campaign Alpha', trustScore: 91, ctr: 1.2, anomalyScore: 0.08, status: 'Trusted' },
  { publisher: 'CAT', campaign: 'Campaign Alpha', trustScore: 58, ctr: 2.8, anomalyScore: 0.48, status: 'Watchlist' },
  { publisher: 'DOG', campaign: 'Campaign Beta',  trustScore: 33, ctr: 8.3, anomalyScore: 0.81, status: 'Suspicious' },
  { publisher: 'OWL', campaign: 'Campaign Beta',  trustScore: 20, ctr: 7.6, anomalyScore: 0.92, status: 'Zero Conversions' },
  { publisher: 'FOX', campaign: 'Campaign Beta',  trustScore: 12, ctr: 9.1, anomalyScore: 0.96, status: 'Bot-Like Activity' },
];

function statusBadgeClass(status: PublisherStatus): string {
  switch (status) {
    case 'Trusted':           return 'status-badge status-badge--trusted';
    case 'Watchlist':         return 'status-badge status-badge--watchlist';
    case 'Suspicious':        return 'status-badge status-badge--suspicious';
    case 'Zero Conversions':  return 'status-badge status-badge--zero-conversions';
    case 'Bot-Like Activity': return 'status-badge status-badge--bot-like';
  }
}

function PublisherDetails() {
  const navigate = useNavigate();

  function handleViewTimeSeries(row: PublisherCampaignRow) {
    navigate(`/dashboard/${encodeURIComponent(row.campaign)}/${encodeURIComponent(row.publisher)}`);
  }

  return (
    <div className="main-content sentinel-page">
      <h1 className="project-title">Publisher — Campaign Details</h1>
      <p className="subtitle">All publisher–campaign trust statuses. Click "View Time Series" to inspect a publisher's data.</p>

      <div className="panel">
        <table className="data-table">
          <thead>
            <tr>
              <th>Publisher</th>
              <th>Campaign</th>
              <th>Status</th>
              <th>Trust Score</th>
              <th>CTR (%)</th>
              <th>Anomaly Score</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {DEMO_ROWS.map(row => (
              <tr key={`${row.publisher}-${row.campaign}`}>
                <td className="pub-name">{row.publisher}</td>
                <td>{row.campaign}</td>
                <td>
                  <span className={statusBadgeClass(row.status)}>
                    {row.status}
                  </span>
                </td>
                <td><strong>{row.trustScore}</strong></td>
                <td>{row.ctr.toFixed(1)}%</td>
                <td>
                  {row.anomalyScore >= 0.5 && <span className="anomaly-arrow">▲ </span>}
                  {row.anomalyScore.toFixed(2)}
                </td>
                <td>
                  <button
                    className="btn btn--inline"
                    onClick={() => handleViewTimeSeries(row)}
                  >
                    View Time Series &rsaquo;
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default PublisherDetails;
