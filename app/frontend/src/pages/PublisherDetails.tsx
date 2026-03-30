import { useNavigate } from 'react-router-dom';
import { useSentinelData } from '../context/SentinelDataContext';
import type { PublisherStatus } from '../types/sentinel';

function statusBadgeClass(status: PublisherStatus): string {
  switch (status) {
    case 'Trusted':          return 'status-badge status-badge--trusted';
    case 'Watchlist':        return 'status-badge status-badge--watchlist';
    case 'CTR Fraud':
    case 'Impression Fraud':
    case 'Click Injection':
    case 'Fraud':            return 'status-badge status-badge--fraud';
  }
}

function PublisherDetails() {
  const navigate = useNavigate();
  const { publishers } = useSentinelData();

  function handleViewTimeSeries(publisherName: string, campaignName: string | null) {
    navigate(`/dashboard/${encodeURIComponent(campaignName ?? '')}/${encodeURIComponent(publisherName)}`);
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
            {publishers.map(pub => (
              <tr key={pub.id}>
                <td className="pub-name">{pub.name}</td>
                <td>{pub.campaignName ?? '—'}</td>
                <td>
                  <span className={statusBadgeClass(pub.status)}>
                    {pub.status}
                  </span>
                </td>
                <td><strong>{pub.trustScore}</strong></td>
                <td>{pub.ctr.toFixed(1)}%</td>
                <td>
                  {pub.anomalyScore >= 0.5 && <span className="anomaly-arrow">▲ </span>}
                  {pub.anomalyScore.toFixed(2)}
                </td>
                <td>
                  <button
                    className="btn btn--inline"
                    onClick={() => handleViewTimeSeries(pub.name, pub.campaignName)}
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
