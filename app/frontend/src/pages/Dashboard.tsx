import { useState, useEffect, useCallback } from 'react';
import Sidebar from '../components/Sidebar';
import TimeSeriesChart from '../components/TimeSeriesChart';
import type { AnomalyEvent } from '../components/AnomalyArea';

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
  publisher_id: string;
  publisher_name: string;
  campaign_id: string;
  campaign_name: string | null;
}

interface ApiRow {
  bucket_timestamp: string;
  impression_count: number;
  click_count: number;
  conversion_count: number;
}

interface ApiAnomalyRow {
  x1: string;
  x2: string;
  label?: string;
  fill?: string;
  stroke?: string;
}

function Dashboard() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [selected, setSelected] = useState<Publisher | null>(null);
  const [data, setData] = useState<DataPoint[]>([]);
  const [anomalies, setAnomalies] = useState<AnomalyEvent[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/publishers`)
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((pubs: ApiPublisher[]) => {
        if (pubs.length === 0) {
          setLoadError('No publishers found. Start the simulation to generate data.');
          return;
        }
        // Group publishers by campaign_id.
        const campaignMap = new Map<string, Campaign>();
        for (const p of pubs) {
          const key = p.campaign_id ?? 'unknown';
          if (!campaignMap.has(key)) {
            campaignMap.set(key, { name: p.campaign_name ?? key, publishers: [] });
          }
          const campaign = campaignMap.get(key)!;
          campaign.publishers.push({
            name: p.publisher_name,
            publisher_id: p.publisher_id,
            campaign_id: p.campaign_id,
            campaign,
          });
        }
        const grouped = Array.from(campaignMap.values());
        setCampaigns(grouped);
        if (grouped.length > 0 && grouped[0].publishers.length > 0) {
          setSelected(grouped[0].publishers[0]);
        }
      })
      .catch(err => setLoadError(`Could not reach backend: ${err.message}`));
  }, []);

  const fetchMetrics = useCallback(() => {
    if (!selected) return;

    const params = new URLSearchParams({
      t: '9999-12-31T23:59:59Z',
      n: String(N_POINTS),
      publisher_id: selected.publisher_id,
      campaign_id: selected.campaign_id,
    });

    fetch(`${API_BASE}/raw-metrics/get-last-n-before?${params}`)
      .then(r => r.json())
      .then((rows: ApiRow[]) => {
        const mappedData = rows.map(row => ({
          x: new Date(row.bucket_timestamp).getTime(),
          impression_count: row.impression_count,
          click_count: row.click_count,
          conversion_count: row.conversion_count,
        }));

        setData(mappedData);

        if (rows.length === 0) {
          setAnomalies([]);
          return;
        }

        const t1 = rows[0].bucket_timestamp;
        const t2 = rows[rows.length - 1].bucket_timestamp;

        const anomalyParams = new URLSearchParams({
          campaign_id: selected.campaign_id,
          t1,
          t2,
        });

        fetch(`${API_BASE}/anomaly-periods/${selected.publisher_id}?${anomalyParams}`)
          .then(r => r.json())
          .then((anomalyRows: ApiAnomalyRow[]) => {
            setAnomalies(anomalyRows.map(row => ({
              x1: new Date(row.x1).getTime(),
              x2: new Date(row.x2).getTime(),
              label: row.label,
              fill: row.fill,
              stroke: row.stroke,
            })));
          });
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
        <div className="main-content">
          {loadError ?? 'Loading publishers…'}
        </div>
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
            <TimeSeriesChart data={data} publisher={selected.name} anomalies={anomalies} />
          </div>
        </div>
      </div>
    </>
  );
}

export default Dashboard;