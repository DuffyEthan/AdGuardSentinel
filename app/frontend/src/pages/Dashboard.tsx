import { useState, useEffect, useCallback } from 'react';
import Sidebar from '../components/Sidebar';
import TimeSeriesChart from '../components/TimeSeriesChart';

const API_BASE = 'http://localhost:8000';
const POLL_MS = 5000;
const N_POINTS = 72; // ~6 hours at 5-min intervals

// Exported so Sidebar can import them
export interface Publisher {
  name: string;
  publisher_id: string;
  campaign_id: string;
  campaign: Campaign;
}

export interface Campaign {
  name: string;
  publishers: Publisher[];
}

export interface DataPoint {
  x: number; // Unix ms timestamp
  impression_count: number;
  click_count: number;
  conversion_count: number;
}

interface ApiPublisher {
  publisher_name: string;
  publisher_id: string;
  campaign_id: string;
}

interface ApiRow {
  bucket_timestamp: string;
  impression_count: number;
  click_count: number;
  conversion_count: number;
}

function Dashboard() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [selected, setSelected] = useState<Publisher | null>(null);
  const [data, setData] = useState<DataPoint[]>([]);

  useEffect(() => {
    fetch(`${API_BASE}/publishers`)
      .then(r => r.json())
      .then((pubs: ApiPublisher[]) => {
        const campaign: Campaign = { name: 'Publishers', publishers: [] };
        campaign.publishers = pubs.map(p => ({
          name: p.publisher_name,
          publisher_id: p.publisher_id,
          campaign_id: p.campaign_id,
          campaign,
        }));
        setCampaigns([campaign]);
        if (campaign.publishers.length > 0) setSelected(campaign.publishers[0]);
      });
  }, []);

  const fetchMetrics = useCallback(() => {
    if (!selected) return;
    const params = new URLSearchParams({
      t: new Date().toISOString(),
      n: String(N_POINTS),
      publisher_id: selected.publisher_id,
      campaign_id: selected.campaign_id,
    });
    fetch(`${API_BASE}/raw-metrics/get-last-n-before?${params}`)
      .then(r => r.json())
      .then((rows: ApiRow[]) => {
        setData(rows.map(row => ({
          x: new Date(row.bucket_timestamp).getTime(),
          impression_count: row.impression_count,
          click_count: row.click_count,
          conversion_count: row.conversion_count,
        })));
      });
  }, [selected]);

  useEffect(() => {
    fetchMetrics();
    const id = setInterval(fetchMetrics, POLL_MS);
    return () => clearInterval(id);
  }, [fetchMetrics]);

  if (!selected) {
    return (
      <div className="with-sidebar">
        <div className="main-content">Loading publishers…</div>
      </div>
    );
  }

  return (
    <>
      <Sidebar campaigns={campaigns} selected={selected} onSelect={setSelected} />
      <div className="with-sidebar">
        <div className="main-content">
          <div>
            <h1 className="project-title">{selected.name}</h1>
            <p className="subtitle">Live time-series data — polling every 5s</p>
          </div>
          <div className="panel">
            <TimeSeriesChart data={data} publisher={selected.name} />
          </div>
        </div>
      </div>
    </>
  );
}

export default Dashboard;
